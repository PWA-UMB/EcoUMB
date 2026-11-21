"""Sprint 3 — RF-29/RF-30: el usuario confirma o corrige el resultado y queda guardado."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.infrastructure.persistence.models import ClassificationModel, WasteItemModel
from app.seed import CATEGORIES, ITEMS
from tests.conftest import JPEG, auth_headers

URL = "/api/v1/classifications"
BAG_BY_ITEM = {i.code: next(c.bag_color for c in CATEGORIES if c.code == i.category) for i in ITEMS}


def classify(client: TestClient, headers: dict[str, str]) -> dict:  # type: ignore[type-arg]
    response = client.post(URL, headers=headers, files={"image": ("f.jpg", JPEG, "image/jpeg")})
    assert response.status_code == 201, response.text
    return response.json()  # type: ignore[no-any-return]


def send(client: TestClient, headers: dict[str, str], classification_id: str, item_code: str):  # type: ignore[no-untyped-def]
    return client.put(
        f"{URL}/{classification_id}/feedback", headers=headers, json={"item_code": item_code}
    )


def other_item(code: str) -> str:
    return next(i.code for i in ITEMS if i.code != code)


def test_a_new_classification_has_no_feedback(client: TestClient, seeded: FastAPI) -> None:
    headers = auth_headers(client)

    assert classify(client, headers)["feedback"] is None


def test_feedback_requires_authentication(client: TestClient, seeded: FastAPI) -> None:
    headers = auth_headers(client)
    record = classify(client, headers)

    response = client.put(f"{URL}/{record['id']}/feedback", json={"item_code": "botella_pet"})

    assert response.status_code == 401


def test_confirming_the_result_is_saved_as_not_corrected(
    client: TestClient, seeded: FastAPI
) -> None:
    headers = auth_headers(client)
    record = classify(client, headers)

    response = send(client, headers, record["id"], record["item"]["code"])

    assert response.status_code == 200
    feedback = response.json()["feedback"]
    assert feedback["was_corrected"] is False
    assert feedback["item"]["code"] == record["item"]["code"]


def test_correcting_the_result_keeps_the_prediction_and_stores_the_right_object(
    client: TestClient, seeded: FastAPI
) -> None:
    headers = auth_headers(client)
    record = classify(client, headers)
    right = other_item(record["item"]["code"])

    body = send(client, headers, record["id"], right).json()

    assert body["item"]["code"] == record["item"]["code"]  # lo que predijo el modelo no cambia
    assert body["feedback"]["was_corrected"] is True
    assert body["feedback"]["item"]["code"] == right
    assert body["feedback"]["category"]["bag_color"] == BAG_BY_ITEM[right]


def test_the_database_keeps_prediction_and_final_answer(
    client: TestClient, seeded: FastAPI
) -> None:
    headers = auth_headers(client)
    record = classify(client, headers)
    right = other_item(record["item"]["code"])
    send(client, headers, record["id"], right)

    with seeded.state.session_factory() as session:
        row = session.scalars(select(ClassificationModel)).one()
        final = session.get(WasteItemModel, row.final_item_id)
        predicted = session.get(WasteItemModel, row.ai_predicted_item_id)
    assert final is not None and predicted is not None
    assert (final.code, predicted.code) == (right, record["item"]["code"])
    assert row.was_corrected is True
    assert row.final_category_id == final.category_id


def test_a_second_answer_replaces_the_first(client: TestClient, seeded: FastAPI) -> None:
    headers = auth_headers(client)
    record = classify(client, headers)
    send(client, headers, record["id"], other_item(record["item"]["code"]))

    body = send(client, headers, record["id"], record["item"]["code"]).json()

    assert body["feedback"]["was_corrected"] is False


def test_the_history_shows_the_feedback(client: TestClient, seeded: FastAPI) -> None:
    headers = auth_headers(client)
    record = classify(client, headers)
    right = other_item(record["item"]["code"])
    send(client, headers, record["id"], right)

    item = client.get(f"{URL}/me", headers=headers).json()["items"][0]

    assert item["feedback"]["item"]["code"] == right


def test_an_unknown_object_is_a_422(client: TestClient, seeded: FastAPI) -> None:
    headers = auth_headers(client)
    record = classify(client, headers)

    response = send(client, headers, record["id"], "unicornio")

    assert response.status_code == 422
    assert response.json() == {"detail": "Objeto de residuo desconocido"}


def test_only_the_owner_can_give_feedback(client: TestClient, seeded: FastAPI) -> None:
    owner = auth_headers(client, email="ana@umb.edu.co")
    stranger = auth_headers(client, email="luis@umb.edu.co")
    record = classify(client, owner)

    response = send(client, stranger, record["id"], "botella_pet")

    assert response.status_code == 404  # no revela que la clasificación existe
    assert classify_feedback_of(client, owner) is None


def classify_feedback_of(client: TestClient, headers: dict[str, str]):  # type: ignore[no-untyped-def]
    return client.get(f"{URL}/me", headers=headers).json()["items"][0]["feedback"]


def test_a_missing_classification_is_a_404(client: TestClient, seeded: FastAPI) -> None:
    headers = auth_headers(client)

    response = send(client, headers, "00000000-0000-4000-8000-000000000000", "botella_pet")

    assert response.status_code == 404


def test_extra_fields_are_rejected(client: TestClient, seeded: FastAPI) -> None:
    headers = auth_headers(client)
    record = classify(client, headers)

    response = client.put(
        f"{URL}/{record['id']}/feedback",
        headers=headers,
        json={"item_code": "botella_pet", "points": 999},
    )

    assert response.status_code == 422
