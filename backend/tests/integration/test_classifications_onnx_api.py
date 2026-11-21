"""Sprint 3 — la API con el clasificador real: no es «simulado» y registra la versión."""

import io
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import func, select

from app.core.config import Settings
from app.infrastructure.persistence.base import Base
from app.infrastructure.persistence.models import ClassificationModel, MlModelVersionModel
from app.main import create_app
from app.seed import seed
from tests.conftest import JPEG, auth_headers
from tests.unit.test_onnx_classifier import build_tiny_model

URL = "/api/v1/classifications"


def png(color: tuple[int, int, int]) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (320, 240), color).save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def onnx_app(tmp_path: Path) -> Iterator[FastAPI]:
    model_dir = tmp_path / "v1"
    model_dir.mkdir()
    build_tiny_model(model_dir / "model.onnx")
    (model_dir / "labels.json").write_text('["cardboard", "glass", "metal"]', encoding="utf-8")
    (model_dir / "class_map.json").write_text(
        '{"cardboard": {"item_code": "carton_limpio", "category": "aprovechable"},'
        ' "glass": {"item_code": "botella_vidrio", "category": "aprovechable"},'
        ' "metal": {"item_code": "lata_aluminio", "category": "aprovechable"}}',
        encoding="utf-8",
    )
    settings = Settings(
        app_env="test",
        database_url="sqlite+pysqlite:///:memory:",
        storage_dir=str(tmp_path / "uploads"),
        classifier="onnx",
        model_dir=str(model_dir),
        _env_file=None,
    )
    application = create_app(settings)
    Base.metadata.create_all(application.state.engine)
    with application.state.session_factory() as session:
        seed(session)
    yield application
    application.state.engine.dispose()


@pytest.fixture
def onnx_client(onnx_app: FastAPI) -> Iterator[TestClient]:
    with TestClient(onnx_app) as client:
        yield client


def upload(client: TestClient, headers: dict[str, str], data: bytes) -> dict:  # type: ignore[type-arg]
    response = client.post(URL, headers=headers, files={"image": ("f.png", data, "image/png")})
    assert response.status_code == 201, response.text
    return response.json()  # type: ignore[no-any-return]


def test_a_real_model_prediction_is_not_marked_as_simulated(onnx_client: TestClient) -> None:
    headers = auth_headers(onnx_client)

    body = upload(onnx_client, headers, png((0, 255, 0)))

    assert body["simulated"] is False
    assert body["model_version"] == "v1"
    assert body["item"]["code"] == "botella_vidrio"  # verde → vidrio en el modelo de prueba
    assert body["category"]["bag_color"] == "blanca"  # la bolsa la decide la base de datos


def test_different_photos_get_different_answers(onnx_client: TestClient) -> None:
    headers = auth_headers(onnx_client)

    red = upload(onnx_client, headers, png((255, 0, 0)))["item"]["code"]
    blue = upload(onnx_client, headers, png((0, 0, 255)))["item"]["code"]

    assert (red, blue) == ("carton_limpio", "lata_aluminio")


def test_the_model_version_is_registered_once_and_linked(
    onnx_client: TestClient, onnx_app: FastAPI
) -> None:
    headers = auth_headers(onnx_client)
    upload(onnx_client, headers, png((255, 0, 0)))
    upload(onnx_client, headers, png((0, 255, 0)))

    with onnx_app.state.session_factory() as session:
        versions = session.scalars(select(MlModelVersionModel)).all()
        linked = session.scalar(
            select(func.count())
            .select_from(ClassificationModel)
            .where(ClassificationModel.model_version_id == versions[0].id)
        )
    assert [v.version for v in versions] == ["v1"]
    assert versions[0].is_active is True
    assert versions[0].model_path == "v1/model.onnx"
    assert linked == 2


def test_the_history_keeps_the_model_version(onnx_client: TestClient) -> None:
    headers = auth_headers(onnx_client)
    upload(onnx_client, headers, png((255, 0, 0)))

    item = onnx_client.get(f"{URL}/me", headers=headers).json()["items"][0]

    assert item["simulated"] is False
    assert item["model_version"] == "v1"


def test_a_corrupt_image_with_a_valid_signature_is_a_422_not_a_500(
    onnx_client: TestClient,
) -> None:
    headers = auth_headers(onnx_client)

    response = onnx_client.post(
        URL, headers=headers, files={"image": ("f.jpg", JPEG, "image/jpeg")}
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "La imagen no se pudo procesar"}
    assert not list(Path(onnx_client.app.state.settings.storage_dir).rglob("*.jpg"))  # type: ignore[attr-defined]


def test_the_simulated_default_has_no_model_version(client: TestClient, seeded: FastAPI) -> None:
    headers = auth_headers(client)

    body = client.post(URL, headers=headers, files={"image": ("f.jpg", JPEG, "image/jpeg")}).json()

    assert body["simulated"] is True
    assert body["model_version"] is None
