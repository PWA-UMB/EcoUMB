"""Seed idempotente: 3 categorías normativas (Res. 2184/2019) y las 15 clases del SAD §7.3.

Uso: ``python -m app.seed``
"""

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.infrastructure.persistence.models import WasteCategoryModel, WasteItemModel
from app.infrastructure.persistence.session import create_db_engine, create_session_factory

logger = logging.getLogger("ecoumb.seed")


@dataclass(frozen=True)
class CategorySeed:
    code: str
    bag_color: str
    description: str
    educational_text: str


@dataclass(frozen=True)
class ItemSeed:
    code: str
    display_name: str
    category: str
    short_message: str
    disposal_tip: str


CATEGORIES: tuple[CategorySeed, ...] = (
    CategorySeed(
        "aprovechable",
        "blanca",
        "Residuos aprovechables: plásticos, papel, cartón, vidrio y metales.",
        "Van en la bolsa blanca los materiales que pueden volver al ciclo productivo, siempre que "
        "estén limpios y secos.",
    ),
    CategorySeed(
        "no_aprovechable",
        "negra",
        "Residuos no aprovechables: los que hoy no se pueden reciclar ni compostar.",
        "Van en la bolsa negra los residuos contaminados con comida, grasa o materiales mixtos "
        "sin proceso de aprovechamiento.",
    ),
    CategorySeed(
        "organico",
        "verde",
        "Residuos orgánicos aprovechables: restos de comida y de poda.",
        "Van en la bolsa verde los residuos que se descomponen y pueden convertirse en compost.",
    ),
)

# Orden = índice de salida del modelo (class_id 0..14), igual a la tabla del SAD §7.3.
ITEMS: tuple[ItemSeed, ...] = (
    ItemSeed(
        "botella_pet",
        "Botella PET",
        "aprovechable",
        "Va en la bolsa blanca porque es plástico reciclable.",
        "Vacíala y aplástala antes de depositarla.",
    ),
    ItemSeed(
        "vaso_plastico",
        "Vaso plástico desechable",
        "aprovechable",
        "Va en la bolsa blanca si está limpio: es un plástico aprovechable.",
        "Enjuágalo para retirar restos de bebida.",
    ),
    ItemSeed(
        "lata_aluminio",
        "Lata de aluminio",
        "aprovechable",
        "Va en la bolsa blanca porque el aluminio se recicla una y otra vez.",
        "Vacíala y aplástala para ahorrar espacio.",
    ),
    ItemSeed(
        "papel_limpio",
        "Papel limpio",
        "aprovechable",
        "Va en la bolsa blanca porque el papel limpio y seco se recicla.",
        "Mantenlo seco y sin grasa.",
    ),
    ItemSeed(
        "carton_limpio",
        "Cartón limpio",
        "aprovechable",
        "Va en la bolsa blanca porque el cartón seco se recicla.",
        "Aplana las cajas antes de depositarlas.",
    ),
    ItemSeed(
        "botella_vidrio",
        "Botella de vidrio",
        "aprovechable",
        "Va en la bolsa blanca porque el vidrio es 100 % reciclable.",
        "Retira la tapa y evita romperla.",
    ),
    ItemSeed(
        "empaque_metalizado",
        "Empaque metalizado de snacks",
        "no_aprovechable",
        "Va en la bolsa negra: es un empaque multicapa difícil de reciclar.",
        "Deposítalo sin arrugarlo en exceso para reducir volumen.",
    ),
    ItemSeed(
        "servilleta_sucia",
        "Servilleta o papel sucio",
        "no_aprovechable",
        "Va en la bolsa negra porque el papel con grasa o comida no se recicla.",
        "Sepáralo del papel limpio para no contaminarlo.",
    ),
    ItemSeed(
        "vaso_cafe_contaminado",
        "Vaso de café desechable contaminado",
        "no_aprovechable",
        "Va en la bolsa negra: tiene restos de bebida y un recubrimiento plástico.",
        "Vacía el líquido antes de depositarlo.",
    ),
    ItemSeed(
        "empaque_comida_residuos",
        "Empaque de comida con residuos",
        "no_aprovechable",
        "Va en la bolsa negra mientras tenga restos de comida.",
        "Si logras dejarlo limpio y seco, puede ir a la bolsa blanca.",
    ),
    ItemSeed(
        "colilla_cigarrillo",
        "Colilla de cigarrillo",
        "no_aprovechable",
        "Va en la bolsa negra: el filtro y las cenizas no son aprovechables.",
        "Asegúrate de que esté completamente apagada.",
    ),
    ItemSeed(
        "cascara_fruta",
        "Cáscara de fruta",
        "organico",
        "Va en la bolsa verde porque es un residuo orgánico compostable.",
        "Deposítala sin bolsas plásticas ni empaques.",
    ),
    ItemSeed(
        "restos_comida",
        "Restos de comida cocinada",
        "organico",
        "Va en la bolsa verde porque los restos de comida se descomponen.",
        "Escurre los líquidos antes de depositarlos.",
    ),
    ItemSeed(
        "bolsa_te_filtro_cafe",
        "Bolsa de té / filtro de café usado",
        "organico",
        "Va en la bolsa verde porque es material orgánico.",
        "Retira grapas, hilos o etiquetas si los tiene.",
    ),
    ItemSeed(
        "residuo_poda",
        "Residuo de poda / hojas",
        "organico",
        "Va en la bolsa verde porque los residuos de jardín se compostan.",
        "Córtalos en trozos pequeños para que ocupen menos.",
    ),
)


@dataclass(frozen=True)
class SeedResult:
    categories_created: int
    items_created: int


def seed(session: Session) -> SeedResult:
    existing_categories = {c.code: c for c in session.scalars(select(WasteCategoryModel))}
    categories_created = 0
    for category in CATEGORIES:
        if category.code not in existing_categories:
            model = WasteCategoryModel(
                code=category.code,
                bag_color=category.bag_color,
                description=category.description,
                educational_text=category.educational_text,
            )
            session.add(model)
            existing_categories[category.code] = model
            categories_created += 1
    session.flush()  # asigna los id de las categorías nuevas

    existing_items = set(session.scalars(select(WasteItemModel.code)))
    items_created = 0
    for class_id, item in enumerate(ITEMS):
        if item.code in existing_items:
            continue
        session.add(
            WasteItemModel(
                class_id=class_id,
                code=item.code,
                display_name=item.display_name,
                category_id=existing_categories[item.category].id,
                short_message=item.short_message,
                disposal_tip=item.disposal_tip,
            )
        )
        items_created += 1
    session.commit()
    return SeedResult(categories_created=categories_created, items_created=items_created)


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    engine = create_db_engine(settings.database_url)
    with create_session_factory(engine)() as session:
        result = seed(session)
    logger.info(
        "seed completado",
        extra={
            "categories_created": result.categories_created,
            "items_created": result.items_created,
        },
    )


if __name__ == "__main__":
    main()
