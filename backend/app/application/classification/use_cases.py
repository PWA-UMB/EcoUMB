"""Casos de uso de clasificación (RF-09 a RF-17). Sin dependencias de frameworks."""

import uuid

from app.application.classification.images import CONTENT_TYPE_BY_EXTENSION, validate_image
from app.domain.confidence import band_for
from app.domain.entities.classification import Classification
from app.domain.errors import CatalogUnavailable, ClassificationNotFound, UnknownWasteItem
from app.domain.ports import (
    ClassificationRepository,
    ImageClassifier,
    ImageStorage,
    WasteCatalog,
)


def classify_waste(
    catalog: WasteCatalog,
    classifier: ImageClassifier,
    storage: ImageStorage,
    repo: ClassificationRepository,
    *,
    user_id: uuid.UUID,
    image: bytes,
    max_bytes: int,
) -> Classification:
    """Valida la imagen, la clasifica, la guarda y registra la clasificación del usuario."""
    validated = validate_image(image, max_bytes=max_bytes)  # antes de tocar almacén o base de datos
    items = catalog.list_active()
    if not items:
        raise CatalogUnavailable
    prediction = classifier.predict(image, items)

    key = f"{user_id}/{uuid.uuid4().hex}.{validated.extension}"
    storage.save(key, image)
    try:
        return repo.add(
            user_id=user_id,
            prediction=prediction,
            band=band_for(prediction.confidence),
            image_key=key,
        )
    except Exception:
        storage.delete(key)  # sin registro no debe quedar un archivo huérfano
        raise


def give_feedback(
    catalog: WasteCatalog,
    repo: ClassificationRepository,
    *,
    user_id: uuid.UUID,
    classification_id: uuid.UUID,
    item_code: str,
) -> Classification:
    """El usuario confirma o corrige el resultado (RF-29) y se guarda su respuesta (RF-30).

    La predicción original no se toca: sirve para medir al modelo y las respuestas, para mejorarlo.
    """
    item = next((i for i in catalog.list_active() if i.code == item_code), None)
    if item is None:
        raise UnknownWasteItem
    record = repo.set_feedback(user_id, classification_id, item.id)
    if record is None:
        raise ClassificationNotFound
    return record


def list_history(
    repo: ClassificationRepository, user_id: uuid.UUID, *, limit: int, offset: int
) -> tuple[list[Classification], int]:
    return repo.list_for_user(user_id, limit=limit, offset=offset)


def get_classification_image(
    repo: ClassificationRepository,
    storage: ImageStorage,
    user_id: uuid.UUID,
    classification_id: uuid.UUID,
) -> tuple[bytes, str]:
    """Bytes y tipo de la imagen. Solo su dueño puede verla (privacidad, SAD §14)."""
    record = repo.get_for_user(user_id, classification_id)
    if record is None:
        raise ClassificationNotFound
    try:
        data = storage.read(record.image_key)
    except FileNotFoundError as error:
        raise ClassificationNotFound from error
    extension = record.image_key.rsplit(".", 1)[-1]
    return data, CONTENT_TYPE_BY_EXTENSION.get(extension, "application/octet-stream")
