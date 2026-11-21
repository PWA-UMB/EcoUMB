from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx2 import Response

from app.core.config import Settings
from app.infrastructure.persistence.base import Base
from app.main import create_app
from app.seed import seed

STRONG_PASSWORD = "Clave-Segura-2026"

# Cabeceras mínimas ("magic bytes") de imágenes válidas: se valida el contenido, no la extensión.
JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + b"\x01" * 64 + b"\xff\xd9"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x02" * 64
WEBP = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"\x03" * 64


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    # bcrypt_rounds queda en su valor por defecto (12): CP-01 verifica ese costo.
    return Settings(
        app_env="test",
        database_url="sqlite+pysqlite:///:memory:",
        cors_origins="http://localhost:5173",
        storage_dir=str(tmp_path / "uploads"),
        _env_file=None,
    )


@pytest.fixture
def app(settings: Settings) -> Iterator[FastAPI]:
    application = create_app(settings)
    Base.metadata.create_all(application.state.engine)
    yield application
    application.state.engine.dispose()


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def seeded(app: FastAPI) -> FastAPI:
    """La aplicación con el catálogo (3 categorías y 15 clases) ya sembrado."""
    with app.state.session_factory() as session:
        seed(session)
    return app


def register(
    client: TestClient,
    email: str = "ana@umb.edu.co",
    password: str = STRONG_PASSWORD,
    full_name: str | None = "Ana Pérez",
) -> Response:
    return client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
    )


def login(
    client: TestClient, email: str = "ana@umb.edu.co", password: str = STRONG_PASSWORD
) -> Response:
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def auth_headers(
    client: TestClient, email: str = "ana@umb.edu.co", full_name: str | None = "Ana Pérez"
) -> dict[str, str]:
    """Registra la cuenta y la inicia sesión; devuelve la cabecera Authorization."""
    register(client, email=email, full_name=full_name)
    token = login(client, email=email).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def settings_storage(settings: Settings) -> Path:
    """Carpeta donde el almacén local guarda las imágenes de la prueba."""
    return Path(settings.storage_dir)
