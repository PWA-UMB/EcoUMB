from dataclasses import dataclass

from app.domain.entities.classification import WasteItem


@dataclass(frozen=True)
class WasteCategory:
    """Una bolsa del código de colores con su texto educativo (guardado en waste_categories)."""

    code: str
    bag_color: str
    description: str
    educational_text: str


@dataclass(frozen=True)
class BagGuide:
    category: WasteCategory
    items: tuple[WasteItem, ...]


@dataclass(frozen=True)
class Normative:
    title: str
    summary: str
    note: str


@dataclass(frozen=True)
class Practice:
    title: str
    text: str


@dataclass(frozen=True)
class EducationContent:
    normative: Normative
    bags: tuple[BagGuide, ...]
    practices: tuple[Practice, ...]
