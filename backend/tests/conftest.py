from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx2 import Response

from app.core.config import Settings
from app.infrastructure.persistence.base import Base
from app.main import create_app

STRONG_PASSWORD = "Clave-Segura-2026"


@pytest.fixture
def settings() -> Settings:
    # bcrypt_rounds queda en su valor por defecto (12): CP-01 verifica ese costo.
    return Settings(
        app_env="test",
        database_url="sqlite+pysqlite:///:memory:",
        cors_origins="http://localhost:5173",
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
