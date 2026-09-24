"""Casos de uso de clasificación probados con dobles en memoria (sin FastAPI ni base de datos)."""

import uuid
from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from app.application.classification.use_cases import (
    classify_waste,
    get_classification_image,
    give_feedback,
    list_history,
)
from app.domain.confidence import ConfidenceBand
from app.domain.entities.classification import (
    Candidate,
    Classification,
    Feedback,
    Prediction,
    RankedItem,
    WasteItem,
)
from app.domain.errors import (
    CatalogUnavailable,
    ClassificationNotFound,
    UnknownWasteItem,
    UnsupportedImageType,
)
from tests.conftest import JPEG


def _item(n: int) -> WasteItem:
    return WasteItem(
        id=uuid.uuid4(),
        class_id=n,
        code=f"item_{n}",
        display_name=f"Objeto {n}",
        category_code="aprovechable",
        bag_color="blanca",
        short_message="Va en la bolsa blanca.",
        disposal_tip="Límpialo.",
        points_value=10,
    )


ITEMS = [_item(n) for n in range(4)]


class FakeCatalog:
    def __init__(self, items: Sequence[WasteItem]) -> None:
        self._items = list(items)

    def list_active(self) -> list[WasteItem]:
        return self._items


class FixedClassifier:
    """Siempre acierta el primer objeto del catálogo con 90 % de confianza."""

    def predict(self, image: bytes, items: Sequence[WasteItem]) -> Prediction:
        first, second, third = items[0], items[1], items[2]
        return Prediction(
            item_id=first.id,
            confidence=0.9,
            top3=(Candidate(first.id, 0.9), Candidate(second.id, 0.06), Candidate(third.id, 0.02)),
        )


class MemoryStorage:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    def save(self, key: str, data: bytes) -> None:
        self.files[key] = data

    def read(self, key: str) -> bytes:
        return self.files[key]

    def delete(self, key: str) -> None:
        self.files.pop(key, None)


class MemoryRepository:
    def __init__(self, *, fail: bool = False) -> None:
        self.rows: list[Classification] = []
        self.fail = fail

    def add(
        self, *, user_id: uuid.UUID, prediction: Prediction, band: ConfidenceBand, image_key: str
    ) -> Classification:
        if self.fail:
            raise RuntimeError("base de datos caída")
        item = next(i for i in ITEMS if i.id == prediction.item_id)
        row = Classification(
            id=uuid.uuid4(),
            user_id=user_id,
            item=item,
            confidence=prediction.confidence,
            band=band,
            top3=tuple(
                RankedItem(next(i for i in ITEMS if i.id == c.item_id), c.confidence)
                for c in prediction.top3
            ),
            image_key=image_key,
            points_awarded=0,
            simulated=True,
            created_at=datetime.now(UTC),
        )
        self.rows.append(row)
        return row

    def list_for_user(
        self, user_id: uuid.UUID, *, limit: int, offset: int
    ) -> tuple[list[Classification], int]:
        mine = [r for r in reversed(self.rows) if r.user_id == user_id]
        return mine[offset : offset + limit], len(mine)

    def get_for_user(
        self, user_id: uuid.UUID, classification_id: uuid.UUID
    ) -> Classification | None:
        return next(
            (r for r in self.rows if r.id == classification_id and r.user_id == user_id), None
        )

    def set_feedback(
        self, user_id: uuid.UUID, classification_id: uuid.UUID, item_id: uuid.UUID
    ) -> Classification | None:
        current = self.get_for_user(user_id, classification_id)
        if current is None:
            return None
        item = next(i for i in ITEMS if i.id == item_id)
        updated = replace(current, feedback=Feedback(item, item.id != current.item.id))
        self.rows[self.rows.index(current)] = updated
        return updated


USER = uuid.uuid4()
LIMIT = 5 * 1024 * 1024


def _classify(
    repo: MemoryRepository, storage: MemoryStorage, image: bytes = JPEG, user: uuid.UUID = USER
) -> Classification:
    return classify_waste(
        FakeCatalog(ITEMS),
        FixedClassifier(),
        storage,
        repo,
        user_id=user,
        image=image,
        max_bytes=LIMIT,
    )


def test_classifying_stores_the_image_and_the_record() -> None:
    repo, storage = MemoryRepository(), MemoryStorage()

    result = _classify(repo, storage)

    assert result.item == ITEMS[0] and result.band is ConfidenceBand.HIGH
    assert repo.rows == [result]
    (key,) = storage.files
    assert key == result.image_key and key.startswith(f"{USER}/") and key.endswith(".jpg")
    assert storage.files[key] == JPEG


def test_an_invalid_image_touches_neither_storage_nor_repository() -> None:
    repo, storage = MemoryRepository(), MemoryStorage()

    with pytest.raises(UnsupportedImageType):
        _classify(repo, storage, image=b"no es una imagen")

    assert repo.rows == [] and storage.files == {}


def test_an_empty_catalog_is_reported() -> None:
    with pytest.raises(CatalogUnavailable):
        classify_waste(
            FakeCatalog([]),
            FixedClassifier(),
            MemoryStorage(),
            MemoryRepository(),
            user_id=USER,
            image=JPEG,
            max_bytes=LIMIT,
        )


def test_the_image_is_removed_if_the_record_cannot_be_saved() -> None:
    """Sin registro no debe quedar un archivo huérfano en el almacén."""
    repo, storage = MemoryRepository(fail=True), MemoryStorage()

    with pytest.raises(RuntimeError):
        _classify(repo, storage)

    assert storage.files == {}


def test_history_is_scoped_to_the_user_and_paginated() -> None:
    repo, storage = MemoryRepository(), MemoryStorage()
    mine = [_classify(repo, storage, JPEG + bytes([n])) for n in range(3)]
    _classify(repo, storage, user=uuid.uuid4())

    page, total = list_history(repo, USER, limit=2, offset=0)

    assert total == 3
    assert [c.id for c in page] == [mine[2].id, mine[1].id]


def test_only_the_owner_gets_the_image_bytes() -> None:
    repo, storage = MemoryRepository(), MemoryStorage()
    created = _classify(repo, storage)

    data, content_type = get_classification_image(repo, storage, USER, created.id)

    assert data == JPEG and content_type == "image/jpeg"
    with pytest.raises(ClassificationNotFound):
        get_classification_image(repo, storage, uuid.uuid4(), created.id)


def test_a_record_whose_file_is_gone_is_reported_as_not_found() -> None:
    repo, storage = MemoryRepository(), MemoryStorage()
    created = _classify(repo, storage)
    storage.files.clear()

    class Gone(MemoryStorage):
        def read(self, key: str) -> bytes:
            raise FileNotFoundError(key)

    with pytest.raises(ClassificationNotFound):
        get_classification_image(repo, Gone(), USER, created.id)


def test_confirming_the_prediction_is_not_a_correction() -> None:
    repo, storage = MemoryRepository(), MemoryStorage()
    created = _classify(repo, storage)

    updated = give_feedback(
        FakeCatalog(ITEMS),
        repo,
        user_id=USER,
        classification_id=created.id,
        item_code=created.item.code,
    )

    assert updated.feedback is not None and updated.feedback.was_corrected is False


def test_a_different_object_is_a_correction_and_keeps_the_prediction() -> None:
    repo, storage = MemoryRepository(), MemoryStorage()
    created = _classify(repo, storage)
    right = next(i for i in ITEMS if i.id != created.item.id)

    updated = give_feedback(
        FakeCatalog(ITEMS), repo, user_id=USER, classification_id=created.id, item_code=right.code
    )

    assert updated.item == created.item
    assert updated.feedback == Feedback(right, True)


def test_an_object_outside_the_catalog_is_rejected_before_touching_the_record() -> None:
    repo, storage = MemoryRepository(), MemoryStorage()
    created = _classify(repo, storage)

    with pytest.raises(UnknownWasteItem):
        give_feedback(
            FakeCatalog(ITEMS), repo, user_id=USER, classification_id=created.id, item_code="nada"
        )
    assert repo.rows[0].feedback is None


def test_feedback_on_someone_elses_classification_is_not_found() -> None:
    repo, storage = MemoryRepository(), MemoryStorage()
    created = _classify(repo, storage)

    with pytest.raises(ClassificationNotFound):
        give_feedback(
            FakeCatalog(ITEMS),
            repo,
            user_id=uuid.uuid4(),
            classification_id=created.id,
            item_code=ITEMS[0].code,
        )
