"""Historia S1-04 — esquema completo y seed (3 categorías, 15 clases)."""

from collections import Counter

from fastapi import FastAPI
from sqlalchemy import inspect, select

from app.infrastructure.persistence.base import Base
from app.infrastructure.persistence.models import WasteCategoryModel, WasteItemModel
from app.seed import seed

SAD_TABLES = {
    "users",
    "waste_categories",
    "waste_items",
    "classifications",
    "rewards",
    "reward_redemptions",
    "achievements",
    "user_achievements",
    "audit_logs",
    "ml_model_versions",
}


def test_model_defines_every_table_of_the_sad(app: FastAPI) -> None:
    assert SAD_TABLES <= set(Base.metadata.tables)
    assert SAD_TABLES <= set(inspect(app.state.engine).get_table_names())


def test_seed_inserts_three_categories_and_fifteen_items(app: FastAPI) -> None:
    with app.state.session_factory() as session:
        seed(session)

        categories = session.scalars(select(WasteCategoryModel)).all()
        items = session.scalars(select(WasteItemModel)).all()

    assert {c.bag_color for c in categories} == {"blanca", "negra", "verde"}
    assert len(items) == 15
    assert sorted(i.class_id for i in items) == list(range(15))


def test_seed_maps_items_to_the_right_bag(app: FastAPI) -> None:
    with app.state.session_factory() as session:
        seed(session)
        rows = session.execute(
            select(WasteItemModel.code, WasteCategoryModel.bag_color).join(
                WasteCategoryModel, WasteItemModel.category_id == WasteCategoryModel.id
            )
        ).all()

    bag_by_code = dict(rows)
    assert bag_by_code["botella_pet"] == "blanca"
    assert bag_by_code["colilla_cigarrillo"] == "negra"
    assert bag_by_code["cascara_fruta"] == "verde"
    assert Counter(bag_by_code.values()) == {"blanca": 6, "negra": 5, "verde": 4}  # SAD §7.3


def test_seed_is_idempotent(app: FastAPI) -> None:
    with app.state.session_factory() as session:
        seed(session)
        second_run = seed(session)
        item_count = len(session.scalars(select(WasteItemModel)).all())

    assert item_count == 15
    assert second_run.categories_created == 0 and second_run.items_created == 0
