"""Módulo educativo (RF-26, RF-27, RF-28). La guía sale del catálogo: no se escribe a mano."""

from app.application.education.content import NORMATIVE, PRACTICES
from app.domain.entities.education import BagGuide, EducationContent
from app.domain.errors import CatalogUnavailable
from app.domain.ports import CategoryCatalog, WasteCatalog

# Orden pedagógico de las bolsas: primero lo que más se recicla.
CATEGORY_ORDER = ("aprovechable", "no_aprovechable", "organico")


def get_education(catalog: WasteCatalog, categories: CategoryCatalog) -> EducationContent:
    items = catalog.list_active()
    known = {c.code: c for c in categories.list_categories()}
    if not items or not known:
        raise CatalogUnavailable
    order = [code for code in CATEGORY_ORDER if code in known]
    order += sorted(code for code in known if code not in CATEGORY_ORDER)
    bags = tuple(
        BagGuide(
            category=known[code],
            items=tuple(
                sorted(
                    (i for i in items if i.category_code == code),
                    key=lambda item: item.display_name,
                )
            ),
        )
        for code in order
    )
    return EducationContent(normative=NORMATIVE, bags=bags, practices=PRACTICES)
