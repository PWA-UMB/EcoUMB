"""Sprint 2 — RF-09/10 (imagen), clasificación simulada, RF-16/17 (registro e historial)."""

import uuid
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import select

from app.infrastructure.persistence.models import ClassificationModel
from app.seed import CATEGORIES, ITEMS
from tests.conftest import JPEG, PNG, WEBP, auth_headers

URL = "/api/v1/classifications"
BAG_BY_ITEM = {i.code: next(c.bag_color for c in CATEGORIES if c.code == i.category) for i in ITEMS}


def upload(
    client: TestClient,
    headers: dict[str, str],
    data: bytes = JPEG,
    filename: str = "foto.jpg",
    content_type: str = "image/jpeg",
) -> Response:
    return client.post(URL, headers=headers, files={"image": (filename, data, content_type)})


# ------------------------------------------------------------------ autenticación
def test_classifying_requires_authentication(client: TestClient, seeded: FastAPI) -> None:
    response = client.post(URL, files={"image": ("foto.jpg", JPEG, "image/jpeg")})

    assert response.status_code == 401


def test_history_requires_authentication(client: TestClient, seeded: FastAPI) -> None:
    assert client.get(f"{URL}/me").status_code == 401


# ------------------------------------------------------------------- clasificación
def test_a_photo_returns_a_simulated_classification(client: TestClient, seeded: FastAPI) -> None:
    headers = auth_headers(client)

    response = upload(client, headers)

    assert response.status_code == 201
    body = response.json()
    uuid.UUID(body["id"])
    assert body["simulated"] is True  # la respuesta declara que aún no es el modelo real
    assert 0 < body["confidence"] < 1
    assert body["confidence_band"] in {"high", "medium", "low"}
    assert body["points_awarded"] == 0  # la gamificación llega en el Sprint 5
    assert {"code", "display_name"} <= body["item"].keys()
    assert body["category"]["bag_color"] in {"blanca", "negra", "verde"}
    assert body["message"] and body["tip"]
    assert len(body["top3"]) == 3
    assert body["image_url"] == f"{URL}/{body['id']}/image"


def test_the_bag_color_comes_from_the_catalog_mapping(client: TestClient, seeded: FastAPI) -> None:
    """El modelo predice el objeto; la bolsa sale del catálogo, no de la predicción (SAD §7.1)."""
    headers = auth_headers(client)

    for n in range(8):
        body = upload(client, headers, data=JPEG + bytes([n]) * 8).json()
        assert body["category"]["bag_color"] == BAG_BY_ITEM[body["item"]["code"]]
        assert body["message"] in {i.short_message for i in ITEMS}


def test_the_same_photo_gets_the_same_answer(client: TestClient, seeded: FastAPI) -> None:
    headers = auth_headers(client)

    first = upload(client, headers).json()
    second = upload(client, headers).json()

    assert first["id"] != second["id"]  # son dos registros distintos
    assert first["item"] == second["item"] and first["confidence"] == second["confidence"]


def test_png_and_webp_are_accepted_too(client: TestClient, seeded: FastAPI) -> None:
    headers = auth_headers(client)

    assert upload(client, headers, PNG, "a.png", "image/png").status_code == 201
    assert upload(client, headers, WEBP, "a.webp", "image/webp").status_code == 201


def test_classification_is_persisted_with_user_date_and_image(
    client: TestClient, seeded: FastAPI, settings_storage: Path
) -> None:
    headers = auth_headers(client)
    me = client.get("/api/v1/users/me", headers=headers).json()

    body = upload(client, headers).json()

    with seeded.state.session_factory() as session:
        row = session.scalars(select(ClassificationModel)).one()
    assert str(row.id) == body["id"]
    assert str(row.user_id) == me["id"]
    assert row.created_at is not None
    assert row.model_version_id is None  # simulada: no hay versión de modelo
    assert row.image_url.startswith(f"{me['id']}/") and row.image_url.endswith(".jpg")
    assert (settings_storage / row.image_url).read_bytes() == JPEG


# ------------------------------------------------------------------- validaciones
def test_unsupported_formats_are_rejected(client: TestClient, seeded: FastAPI) -> None:
    headers = auth_headers(client)

    assert (
        upload(client, headers, b"GIF89a" + b"\x00" * 30, "a.gif", "image/gif").status_code == 415
    )
    assert upload(client, headers, b"texto plano", "nota.txt", "text/plain").status_code == 415


def test_a_disguised_file_is_rejected_by_its_content(client: TestClient, seeded: FastAPI) -> None:
    headers = auth_headers(client)

    response = upload(client, headers, b"#!/bin/sh\necho hola\n", "virus.jpg", "image/jpeg")

    assert response.status_code == 415


def test_empty_file_is_rejected(client: TestClient, seeded: FastAPI) -> None:
    assert upload(client, auth_headers(client), b"").status_code == 422


def test_missing_file_field_is_rejected(client: TestClient, seeded: FastAPI) -> None:
    response = client.post(URL, headers=auth_headers(client), data={"otra": "cosa"})

    assert response.status_code == 422


def test_oversized_image_is_rejected(client: TestClient, seeded: FastAPI) -> None:
    headers = auth_headers(client)
    seeded.state.settings = seeded.state.settings.model_copy(update={"max_image_bytes": 1024})

    assert upload(client, headers, JPEG + b"\x00" * 2000).status_code == 413


def test_huge_upload_is_rejected_before_reading_the_body(
    client: TestClient, seeded: FastAPI
) -> None:
    headers = auth_headers(client)
    seeded.state.settings = seeded.state.settings.model_copy(update={"max_image_bytes": 1024})

    response = upload(client, headers, JPEG + b"\x00" * 200_000)

    assert response.status_code == 413


def test_nothing_is_stored_when_the_image_is_rejected(
    client: TestClient, seeded: FastAPI, settings_storage: Path
) -> None:
    headers = auth_headers(client)
    upload(client, headers, b"no soy una imagen", "x.jpg", "image/jpeg")

    with seeded.state.session_factory() as session:
        assert session.scalars(select(ClassificationModel)).all() == []
    assert not list(settings_storage.rglob("*.*"))


def test_service_is_unavailable_without_a_catalog(client: TestClient, app: FastAPI) -> None:
    """Base sin sembrar: no hay clases que predecir."""
    assert upload(client, auth_headers(client)).status_code == 503


# ---------------------------------------------------------------------- límite de tasa
def test_classification_is_rate_limited_per_user(client: TestClient, seeded: FastAPI) -> None:
    ana = auth_headers(client, "ana@umb.edu.co")
    luis = auth_headers(client, "luis@umb.edu.co", "Luis")

    statuses = [upload(client, ana, JPEG + bytes([n])).status_code for n in range(11)]

    assert statuses[:10] == [201] * 10
    assert statuses[10] == 429
    assert upload(client, luis).status_code == 201  # el límite es por usuario, no global


# -------------------------------------------------------------------------- historial
def test_history_is_empty_at_first(client: TestClient, seeded: FastAPI) -> None:
    body = client.get(f"{URL}/me", headers=auth_headers(client)).json()

    assert body == {"items": [], "total": 0, "limit": 20, "offset": 0}


def test_history_lists_only_my_records_newest_first(client: TestClient, seeded: FastAPI) -> None:
    ana = auth_headers(client, "ana@umb.edu.co")
    luis = auth_headers(client, "luis@umb.edu.co", "Luis")
    created = [upload(client, ana, JPEG + bytes([n])).json()["id"] for n in range(3)]
    upload(client, luis)

    body = client.get(f"{URL}/me", headers=ana).json()

    assert body["total"] == 3
    assert [item["id"] for item in body["items"]] == list(reversed(created))
    item = body["items"][0]
    assert {
        "id",
        "created_at",
        "item",
        "category",
        "confidence",
        "confidence_band",
        "simulated",
    } <= item.keys()


def test_history_is_paginated(client: TestClient, seeded: FastAPI) -> None:
    headers = auth_headers(client)
    ids = [upload(client, headers, JPEG + bytes([n])).json()["id"] for n in range(5)]
    newest_first = list(reversed(ids))

    page = client.get(f"{URL}/me", headers=headers, params={"limit": 2, "offset": 2}).json()

    assert page["total"] == 5 and page["limit"] == 2 and page["offset"] == 2
    assert [i["id"] for i in page["items"]] == newest_first[2:4]


def test_history_rejects_out_of_range_paging(client: TestClient, seeded: FastAPI) -> None:
    headers = auth_headers(client)

    for params in ({"limit": 0}, {"limit": 101}, {"offset": -1}):
        assert client.get(f"{URL}/me", headers=headers, params=params).status_code == 422


# ------------------------------------------------------------------------ imagen guardada
def test_owner_can_download_the_stored_image(client: TestClient, seeded: FastAPI) -> None:
    headers = auth_headers(client)
    created = upload(client, headers, PNG, "a.png", "image/png").json()

    response = client.get(created["image_url"], headers=headers)

    assert response.status_code == 200
    assert response.content == PNG
    assert response.headers["content-type"] == "image/png"
    assert response.headers["cache-control"] == "private, max-age=3600"


def test_another_user_cannot_see_my_image(client: TestClient, seeded: FastAPI) -> None:
    ana = auth_headers(client, "ana@umb.edu.co")
    luis = auth_headers(client, "luis@umb.edu.co", "Luis")
    created = upload(client, ana).json()

    assert (
        client.get(created["image_url"], headers=luis).status_code == 404
    )  # ni siquiera se confirma que existe
    assert client.get(created["image_url"]).status_code == 401


def test_unknown_or_malformed_image_id(client: TestClient, seeded: FastAPI) -> None:
    headers = auth_headers(client)

    assert client.get(f"{URL}/{uuid.uuid4()}/image", headers=headers).status_code == 404
    assert client.get(f"{URL}/no-es-un-uuid/image", headers=headers).status_code == 422
