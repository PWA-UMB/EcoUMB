"""Historias S1-05 (API base) y S1-09 (RBAC)."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.domain.roles import Role
from app.infrastructure.persistence.models import UserModel
from tests.conftest import login, register


def _bearer(client: TestClient, email: str = "ana@umb.edu.co") -> dict[str, str]:
    token = login(client, email=email).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _promote(app: FastAPI, email: str, role: Role) -> None:
    with app.state.session_factory() as session:
        user = session.scalars(select(UserModel).where(UserModel.email == email)).one()
        user.role = role
        session.commit()


# ----------------------------------------------------------------------- /users/me
def test_me_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/users/me")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_me_returns_profile_of_the_token_owner(client: TestClient) -> None:
    register(client)

    body = client.get("/api/v1/users/me", headers=_bearer(client)).json()

    assert body["email"] == "ana@umb.edu.co"
    assert body["full_name"] == "Ana Pérez"
    assert body["total_points"] == 0 and body["level"] == 1
    assert "password_hash" not in body


def test_refresh_token_cannot_be_used_as_bearer(client: TestClient) -> None:
    register(client)
    refresh = login(client).json()["refresh_token"]

    response = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {refresh}"})

    assert response.status_code == 401


def test_garbage_bearer_is_rejected(client: TestClient) -> None:
    response = client.get("/api/v1/users/me", headers={"Authorization": "Bearer abc.def.ghi"})

    assert response.status_code == 401


# --------------------------------------------------------------------------- RBAC
def test_regular_user_cannot_list_users(client: TestClient) -> None:
    register(client)

    assert client.get("/api/v1/users", headers=_bearer(client)).status_code == 403


def test_admin_can_list_users(client: TestClient, app: FastAPI) -> None:
    register(client)
    _promote(app, "ana@umb.edu.co", Role.ADMIN)

    response = client.get("/api/v1/users", headers=_bearer(client))

    assert response.status_code == 200
    assert [u["email"] for u in response.json()] == ["ana@umb.edu.co"]


def test_role_change_takes_effect_for_existing_tokens(client: TestClient, app: FastAPI) -> None:
    """El rol se lee de la base, no del token: un usuario degradado pierde acceso de inmediato."""
    register(client)
    _promote(app, "ana@umb.edu.co", Role.ADMIN)
    headers = _bearer(client)
    assert client.get("/api/v1/users", headers=headers).status_code == 200

    _promote(app, "ana@umb.edu.co", Role.USER)

    assert client.get("/api/v1/users", headers=headers).status_code == 403


# ------------------------------------------------------------------------- health
def test_health_liveness(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_readiness_checks_database(client: TestClient) -> None:
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["database"] == "ok"


def test_openapi_documents_auth_endpoints(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]

    for path in ("/api/v1/auth/register", "/api/v1/auth/login", "/api/v1/auth/refresh"):
        assert path in paths
    assert client.get("/docs").status_code == 200


# -------------------------------------------------------------------------- CORS
def test_cors_allows_only_configured_origins(client: TestClient) -> None:
    allowed = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    denied = client.options(
        "/api/v1/auth/login",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"},
    )

    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "access-control-allow-origin" not in denied.headers


def test_health_readiness_reports_database_failure(client: TestClient, app: FastAPI) -> None:
    def broken_session_factory() -> None:
        raise RuntimeError("base de datos caída")

    app.state.session_factory = broken_session_factory

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "database": "error"}
