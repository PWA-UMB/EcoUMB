"""Historia S1-06 — registro, login y refresh. Los CP-01..CP-05 corresponden a la Guía 5 §3.2."""

import uuid
from datetime import timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.domain.roles import Role
from app.infrastructure.persistence.models import UserModel
from app.infrastructure.security.tokens import JwtTokenService
from tests.conftest import STRONG_PASSWORD, login, register


def _count_users(app: FastAPI) -> int:
    with app.state.session_factory() as session:
        return int(session.scalar(select(func.count()).select_from(UserModel)) or 0)


# --------------------------------------------------------------------------- CP-01
def test_register_success(client: TestClient, app: FastAPI) -> None:
    response = register(client)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "ana@umb.edu.co"
    assert body["role"] == "user"
    assert "password" not in body and "password_hash" not in body

    with app.state.session_factory() as session:
        stored = session.scalars(select(UserModel)).one()
    assert stored.password_hash.startswith("$2b$12$")  # bcrypt, cost factor 12
    assert stored.password_hash != STRONG_PASSWORD


# --------------------------------------------------------------------------- CP-02
def test_register_duplicate_email(client: TestClient, app: FastAPI) -> None:
    assert register(client).status_code == 201

    duplicate = register(client, email="ANA@umb.edu.co")  # mismo correo, otra capitalización

    assert duplicate.status_code == 409
    assert _count_users(app) == 1


# --------------------------------------------------------------------------- CP-03
def test_login_success(client: TestClient, app: FastAPI) -> None:
    register(client)

    response = login(client)

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    tokens: JwtTokenService = app.state.token_service
    access = tokens.decode_access(body["access_token"])
    refresh = tokens.decode_refresh(body["refresh_token"])
    assert access.expires_at - access.issued_at == timedelta(minutes=15)
    assert refresh.expires_at - refresh.issued_at == timedelta(days=7)
    assert body["expires_in"] == 15 * 60


# --------------------------------------------------------------------------- CP-04
def test_login_invalid_credentials(client: TestClient) -> None:
    register(client)

    wrong_password = login(client, password="Otra-Clave-999")
    unknown_email = login(client, email="nadie@umb.edu.co")

    assert wrong_password.status_code == 401
    assert unknown_email.status_code == 401
    # El mensaje no revela cuál de los dos campos falló.
    assert wrong_password.json() == unknown_email.json()


# --------------------------------------------------------------------------- CP-05
def test_refresh_token(client: TestClient, app: FastAPI) -> None:
    register(client)
    tokens = login(client).json()

    ok = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert ok.status_code == 200
    new_access = ok.json()["access_token"]
    me = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {new_access}"})
    assert me.status_code == 200

    invalid = client.post("/api/v1/auth/refresh", json={"refresh_token": "no.es.un.token"})
    assert invalid.status_code == 401

    service: JwtTokenService = app.state.token_service
    expired_service = JwtTokenService(
        private_key=service.private_key,
        public_key=service.public_key,
        access_ttl=timedelta(minutes=15),
        refresh_ttl=timedelta(seconds=-1),
    )
    user_id = me.json()["id"]
    expired = expired_service.create_refresh_token(user_id=uuid.UUID(user_id), role=Role.USER)
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": expired}).status_code == 401


def test_refresh_endpoint_rejects_an_access_token(client: TestClient) -> None:
    register(client)
    tokens = login(client).json()

    response = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["access_token"]})

    assert response.status_code == 401


# ----------------------------------------------------------------- validación (422)
@pytest.mark.parametrize(
    "password",
    # menos de 8 · sin dígito · sin letra · más de 72 bytes (41 caracteres de 2 bytes)
    ["corta1", "sinnumeros-largos", "12345678901", "á" * 40 + "1"],
)
def test_register_rejects_weak_or_oversized_password(client: TestClient, password: str) -> None:
    assert register(client, password=password).status_code == 422


def test_register_rejects_invalid_email(client: TestClient) -> None:
    assert register(client, email="no-es-correo").status_code == 422


def test_register_cannot_choose_own_role(client: TestClient, app: FastAPI) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "eve@umb.edu.co", "password": STRONG_PASSWORD, "role": "admin"},
    )

    assert response.status_code == 422
    assert _count_users(app) == 0


def test_inactive_user_cannot_login(client: TestClient, app: FastAPI) -> None:
    register(client)
    with app.state.session_factory() as session:
        user = session.scalars(select(UserModel)).one()
        user.is_active = False
        session.commit()

    assert login(client).status_code == 401


# ------------------------------------------------------------------ rate limiting
def test_auth_endpoints_are_rate_limited(client: TestClient) -> None:
    def attempt() -> int:
        return login(client, email="x@umb.edu.co", password="Mala-Clave-1").status_code

    statuses = [attempt() for _ in range(11)]

    assert statuses[:10] == [401] * 10
    assert statuses[10] == 429
    blocked = login(client, email="x@umb.edu.co", password="Mala-Clave-1")
    assert "retry-after" in blocked.headers
