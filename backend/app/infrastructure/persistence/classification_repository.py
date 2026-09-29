import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.confidence import ConfidenceBand, band_for
from app.domain.entities.classification import (
    Classification,
    Feedback,
    ModelInfo,
    Prediction,
    RankedItem,
    WasteItem,
)
from app.domain.errors import CatalogUnavailable
from app.infrastructure.persistence.catalog import SqlAlchemyWasteCatalog
from app.infrastructure.persistence.models import (
    ClassificationModel,
    MlModelVersionModel,
    WasteItemModel,
)


def _aware(moment: datetime) -> datetime:
    """SQLite devuelve fechas sin zona horaria; PostgreSQL con ella. Se normaliza a UTC."""
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


class SqlAlchemyClassificationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._catalog = SqlAlchemyWasteCatalog(session)

    def add(
        self, *, user_id: uuid.UUID, prediction: Prediction, band: ConfidenceBand, image_key: str
    ) -> Classification:
        item_row = self._session.get(WasteItemModel, prediction.item_id)
        if item_row is None:
            raise CatalogUnavailable
        model = ClassificationModel(
            user_id=user_id,
            image_url=image_key,  # clave en el almacén; la API no expone rutas internas
            ai_predicted_item_id=item_row.id,
            ai_predicted_category_id=item_row.category_id,
            confidence=Decimal(str(prediction.confidence)),
            top3_predictions=[
                {"item_id": str(c.item_id), "confidence": c.confidence} for c in prediction.top3
            ],
            confidence_band=band,
            model_version_id=self._model_version_id(prediction.model),
            points_awarded=0,  # los puntos llegan con la gamificación (Sprint 5)
            created_at=datetime.now(UTC),  # con microsegundos: el historial ordena de forma estable
        )
        self._session.add(model)
        self._session.commit()
        return self._to_entities([model])[0]

    def set_feedback(
        self, user_id: uuid.UUID, classification_id: uuid.UUID, item_id: uuid.UUID
    ) -> Classification | None:
        row = self._session.scalars(
            select(ClassificationModel).where(
                ClassificationModel.id == classification_id, ClassificationModel.user_id == user_id
            )
        ).first()
        item_row = self._session.get(WasteItemModel, item_id)
        if row is None or item_row is None:
            return None
        row.final_item_id = item_row.id
        row.final_category_id = item_row.category_id
        row.was_corrected = item_row.id != row.ai_predicted_item_id
        self._session.commit()
        return self._to_entities([row])[0]

    def _model_version_id(self, info: ModelInfo | None) -> uuid.UUID | None:
        """Fila de ml_model_versions de la versión que predijo (se crea la primera vez)."""
        if info is None:
            return None  # predicción simulada: sin versión de modelo
        row = self._session.scalars(
            select(MlModelVersionModel).where(MlModelVersionModel.version == info.version)
        ).first()
        if row is None:
            row = MlModelVersionModel(
                version=info.version,
                accuracy=Decimal(str(info.accuracy)) if info.accuracy is not None else None,
                f1_per_class=info.f1_per_class,
                trained_at=datetime.now(UTC),
                model_path=info.path,
                is_active=True,
            )
            self._session.add(row)
            self._session.flush()
        return row.id

    def list_for_user(
        self, user_id: uuid.UUID, *, limit: int, offset: int
    ) -> tuple[list[Classification], int]:
        total = self._session.scalar(
            select(func.count())
            .select_from(ClassificationModel)
            .where(ClassificationModel.user_id == user_id)
        )
        rows = self._session.scalars(
            select(ClassificationModel)
            .where(ClassificationModel.user_id == user_id)
            .order_by(ClassificationModel.created_at.desc(), ClassificationModel.id)
            .limit(limit)
            .offset(offset)
        ).all()
        return self._to_entities(list(rows)), int(total or 0)

    def get_for_user(
        self, user_id: uuid.UUID, classification_id: uuid.UUID
    ) -> Classification | None:
        row = self._session.scalars(
            select(ClassificationModel).where(
                ClassificationModel.id == classification_id, ClassificationModel.user_id == user_id
            )
        ).first()
        return self._to_entities([row])[0] if row else None

    def _to_entities(self, rows: list[ClassificationModel]) -> list[Classification]:
        wanted: set[uuid.UUID] = set()
        for row in rows:
            if row.ai_predicted_item_id:
                wanted.add(row.ai_predicted_item_id)
            if row.final_item_id:
                wanted.add(row.final_item_id)
            wanted.update(uuid.UUID(entry["item_id"]) for entry in row.top3_predictions or [])
        items = self._catalog.get_many(wanted)
        version_ids = {r.model_version_id for r in rows if r.model_version_id}
        versions = {
            v.id: v.version
            for v in self._session.scalars(
                select(MlModelVersionModel).where(MlModelVersionModel.id.in_(version_ids))
            )
        }
        return [_entity(row, items, versions) for row in rows]


def _entity(
    row: ClassificationModel, items: dict[uuid.UUID, WasteItem], versions: dict[uuid.UUID, str]
) -> Classification:
    assert (
        row.ai_predicted_item_id is not None
    )  # toda clasificación guardada tiene su predicción  # noqa: S101
    confidence = float(row.confidence or 0)
    top3 = tuple(
        RankedItem(items[uuid.UUID(entry["item_id"])], float(entry["confidence"]))
        for entry in row.top3_predictions or []
    )
    return Classification(
        id=row.id,
        user_id=row.user_id,
        item=items[row.ai_predicted_item_id],
        confidence=confidence,
        band=row.confidence_band or band_for(confidence),
        top3=top3,
        image_key=row.image_url,
        points_awarded=row.points_awarded,
        simulated=row.model_version_id is None,
        created_at=_aware(row.created_at),
        model_version=versions.get(row.model_version_id) if row.model_version_id else None,
        feedback=(
            Feedback(items[row.final_item_id], row.was_corrected) if row.final_item_id else None
        ),
    )
