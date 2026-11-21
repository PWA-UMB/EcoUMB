import uuid
from dataclasses import dataclass
from datetime import datetime

from app.domain.confidence import ConfidenceBand


@dataclass(frozen=True)
class WasteItem:
    """Una clase del catálogo (lo que predice el modelo) con la bolsa que le corresponde."""

    id: uuid.UUID
    class_id: int
    code: str
    display_name: str
    category_code: str
    bag_color: str
    short_message: str
    disposal_tip: str
    points_value: int


@dataclass(frozen=True)
class Candidate:
    item_id: uuid.UUID
    confidence: float


@dataclass(frozen=True)
class ModelInfo:
    """Versión del modelo real que produjo una predicción (tabla ml_model_versions)."""

    version: str
    path: str
    accuracy: float | None = None
    f1_per_class: dict[str, float] | None = None


@dataclass(frozen=True)
class Prediction:
    """Salida del clasificador: mejor objeto y top-3. `model` es None si es simulada."""

    item_id: uuid.UUID
    confidence: float
    top3: tuple[Candidate, ...]
    model: ModelInfo | None = None


@dataclass(frozen=True)
class RankedItem:
    item: WasteItem
    confidence: float


@dataclass(frozen=True)
class Feedback:
    """La respuesta del usuario: qué era realmente el residuo (RF-29, RF-30)."""

    item: WasteItem
    was_corrected: bool  # False = el usuario confirmó lo que predijo el modelo


@dataclass(frozen=True)
class Classification:
    id: uuid.UUID
    user_id: uuid.UUID
    item: WasteItem
    confidence: float
    band: ConfidenceBand
    top3: tuple[RankedItem, ...]
    image_key: str
    points_awarded: int
    simulated: bool  # True mientras no exista una versión de modelo real detrás
    created_at: datetime
    model_version: str | None = None
    feedback: Feedback | None = None
