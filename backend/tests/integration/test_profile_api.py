"""Sprint 2 — RF-04: visualizar y editar el perfil."""

from fastapi.testclient import TestClient

from tests.conftest import auth_headers

URL = "/api/v1/users/me"


def test_profile_update_requires_authentication(client: TestClient) -> None:
    assert client.patch(URL, json={"full_name": "Nuevo"}).status_code == 401


def test_user_can_change_the_display_name(client: TestClient) -> None:
    headers = auth_headers(client)

    response = client.patch(URL, headers=headers, json={"full_name": "  Ana María Pérez  "})

    assert response.status_code == 200
    assert response.json()["full_name"] == "Ana María Pérez"  # se recortan los espacios
    assert client.get(URL, headers=headers).json()["full_name"] == "Ana María Pérez"  # persistió


def test_blank_name_clears_it(client: TestClient) -> None:
    headers = auth_headers(client)

    response = client.patch(URL, headers=headers, json={"full_name": "   "})

    assert response.status_code == 200
    assert response.json()["full_name"] is None


def test_null_name_clears_it(client: TestClient) -> None:
    headers = auth_headers(client)

    assert client.patch(URL, headers=headers, json={"full_name": None}).json()["full_name"] is None


def test_name_longer_than_120_characters_is_rejected(client: TestClient) -> None:
    headers = auth_headers(client)

    assert client.patch(URL, headers=headers, json={"full_name": "a" * 121}).status_code == 422


def test_fields_that_must_not_change_are_rejected(client: TestClient) -> None:
    """Correo, rol y puntos no se editan desde el perfil (evita escalar privilegios)."""
    headers = auth_headers(client)

    for forbidden in (
        {"email": "otro@umb.edu.co"},
        {"role": "admin"},
        {"total_points": 9999},
        {"level": 99},
    ):
        response = client.patch(URL, headers=headers, json={"full_name": "Ana", **forbidden})
        assert response.status_code == 422, forbidden

    me = client.get(URL, headers=headers).json()
    assert me["role"] == "user" and me["total_points"] == 0 and me["email"] == "ana@umb.edu.co"


def test_the_name_field_is_required(client: TestClient) -> None:
    assert client.patch(URL, headers=auth_headers(client), json={}).status_code == 422


def test_one_user_cannot_edit_another(client: TestClient) -> None:
    ana = auth_headers(client, "ana@umb.edu.co", "Ana")
    luis = auth_headers(client, "luis@umb.edu.co", "Luis")

    client.patch(URL, headers=ana, json={"full_name": "Solo Ana"})

    assert client.get(URL, headers=luis).json()["full_name"] == "Luis"
