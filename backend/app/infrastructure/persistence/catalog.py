import uuid
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.classification import WasteItem
from app.domain.entities.education import WasteCategory
from app.infrastructure.persistence.models import WasteCategoryModel, WasteItemModel


def to_waste_item(item: WasteItemModel, category: WasteCategoryModel) -> WasteItem:
    return WasteItem(
        id=item.id,
        class_id=item.class_id,
        code=item.code,
        display_name=item.display_name,
        category_code=category.code,
        bag_color=category.bag_color,
        short_message=item.short_message,
        disposal_tip=item.disposal_tip,
        points_value=item.points_value,
    )


class SqlAlchemyWasteCatalog:
    """Catálogo de objetos y su bolsa: la normativa vive en datos, no en el modelo (SAD §7.1)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_active(self) -> list[WasteItem]:
        rows = self._session.execute(
            select(WasteItemModel, WasteCategoryModel)
            .join(WasteCategoryModel, WasteItemModel.category_id == WasteCategoryModel.id)
            .where(WasteItemModel.is_active.is_(True))
            .order_by(WasteItemModel.class_id)
        ).all()
        return [to_waste_item(item, category) for item, category in rows]

    def list_categories(self) -> list[WasteCategory]:
        rows = self._session.scalars(select(WasteCategoryModel)).all()
        return [WasteCategory(r.code, r.bag_color, r.description, r.educational_text) for r in rows]

    def get_many(self, ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, WasteItem]:
        wanted = set(ids)
        if not wanted:
            return {}
        rows = self._session.execute(
            select(WasteItemModel, WasteCategoryModel)
            .join(WasteCategoryModel, WasteItemModel.category_id == WasteCategoryModel.id)
            .where(WasteItemModel.id.in_(wanted))
        ).all()
        return {item.id: to_waste_item(item, category) for item, category in rows}
