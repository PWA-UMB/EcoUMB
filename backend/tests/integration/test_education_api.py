"""Sprint 3 — módulo educativo: RF-26 (información), RF-27 (colores), RF-28 (buenas prácticas)."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import update

from app.infrastructure.persistence.models import WasteItemModel
from app.seed import CATEGORIES, ITEMS
from tests.conftest import auth_headers

URL = "/api/v1/education"


def test_the_education_content_requires_authentication(client: TestClient, seeded: FastAPI) -> None:
    assert client.get(URL).status_code == 401


def test_it_presents_the_colombian_color_code(client: TestClient, seeded: FastAPI) -> None:
    body = client.get(URL, headers=auth_headers(client)).json()

    assert "2184" in body["normative"]["title"]  # RF-27: normativa vigente
    assert body["normative"]["summary"]
    assert [b["bag_color"] for b in body["bags"]] == ["blanca", "negra", "verde"]
    assert [b["category"] for b in body["bags"]] == ["aprovechable", "no_aprovechable", "organico"]


def test_each_bag_explains_itself_from_the_database(client: TestClient, seeded: FastAPI) -> None:
    body = client.get(URL, headers=auth_headers(client)).json()

    for bag in body["bags"]:
        seed_category = next(c for c in CATEGORIES if c.code == bag["category"])
        assert bag["description"] == seed_category.description  # RF-26: texto guardado en la base
        assert bag["educational_text"] == seed_category.educational_text


def test_each_bag_lists_the_objects_that_belong_in_it(client: TestClient, seeded: FastAPI) -> None:
    body = client.get(URL, headers=auth_headers(client)).json()

    listed = {i["code"]: b["category"] for b in body["bags"] for i in b["items"]}
    assert listed == {item.code: item.category for item in ITEMS}  # los 15, cada uno en su bolsa
    sample = body["bags"][0]["items"][0]
    assert set(sample) == {"code", "display_name", "disposal_tip"}
    assert sample["disposal_tip"]


def test_deactivated_objects_are_no_longer_taught(client: TestClient, seeded: FastAPI) -> None:
    """La guía sale de la base de datos: desactivar un objeto es un UPDATE, no código."""
    with seeded.state.session_factory() as session:
        session.execute(
            update(WasteItemModel)
            .where(WasteItemModel.code == "botella_pet")
            .values(is_active=False)
        )
        session.commit()

    body = client.get(URL, headers=auth_headers(client)).json()

    listed = {i["code"] for b in body["bags"] for i in b["items"]}
    assert "botella_pet" not in listed
    assert len(listed) == len(ITEMS) - 1


def test_it_includes_environmental_good_practices(client: TestClient, seeded: FastAPI) -> None:
    body = client.get(URL, headers=auth_headers(client)).json()

    assert len(body["practices"]) >= 5  # RF-28
    for practice in body["practices"]:
        assert practice["title"]
        assert practice["text"]


def test_without_a_seeded_catalog_it_is_a_503_not_an_empty_page(client: TestClient) -> None:
    response = client.get(URL, headers=auth_headers(client))

    assert response.status_code == 503
