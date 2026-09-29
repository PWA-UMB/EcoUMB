"""Exportación del dataset de fotos etiquetadas por los usuarios (RF-31)."""

import csv
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.infrastructure.dataset_export import MANIFEST, export_feedback
from app.infrastructure.storage.local import LocalImageStorage
from app.seed import ITEMS
from tests.conftest import JPEG, PNG, auth_headers

URL = "/api/v1/classifications"


def classify(
    client: TestClient, headers: dict[str, str], data: bytes, name: str, kind: str
) -> dict:  # type: ignore[type-arg]
    response = client.post(URL, headers=headers, files={"image": (name, data, kind)})
    assert response.status_code == 201
    return response.json()  # type: ignore[no-any-return]


def label(client: TestClient, headers: dict[str, str], record_id: str, code: str) -> None:
    response = client.put(f"{URL}/{record_id}/feedback", headers=headers, json={"item_code": code})
    assert response.status_code == 200


def export(app: FastAPI, out: Path, *, only_corrected: bool = False):  # type: ignore[no-untyped-def]
    storage = LocalImageStorage(Path(app.state.settings.storage_dir))
    with app.state.session_factory() as session:
        return export_feedback(session, storage, out, only_corrected=only_corrected)


def test_only_photos_with_feedback_are_exported_into_their_real_object_folder(
    client: TestClient, seeded: FastAPI, tmp_path: Path
) -> None:
    headers = auth_headers(client)
    first = classify(client, headers, JPEG, "a.jpg", "image/jpeg")
    second = classify(client, headers, PNG, "b.png", "image/png")
    classify(client, headers, JPEG + b"x", "c.jpg", "image/jpeg")  # sin respuesta: no se exporta
    label(client, headers, first["id"], "lata_aluminio")
    label(client, headers, second["id"], "cascara_fruta")

    summary = export(seeded, tmp_path / "out")

    assert summary.exported == 2 and summary.skipped_missing_file == 0
    assert summary.per_label == {"lata_aluminio": 1, "cascara_fruta": 1}
    assert (tmp_path / "out" / "lata_aluminio" / f"{first['id']}.jpg").read_bytes() == JPEG
    assert (tmp_path / "out" / "cascara_fruta" / f"{second['id']}.png").read_bytes() == PNG


def test_the_manifest_records_labels_without_user_identifiers(
    client: TestClient, seeded: FastAPI, tmp_path: Path
) -> None:
    headers = auth_headers(client, email="privada@umb.edu.co")
    record = classify(client, headers, JPEG, "a.jpg", "image/jpeg")
    right = next(i.code for i in ITEMS if i.code != record["item"]["code"])
    label(client, headers, record["id"], right)

    export(seeded, tmp_path / "out")

    text = (tmp_path / "out" / MANIFEST).read_text(encoding="utf-8")
    rows = list(csv.DictReader(text.splitlines()))
    assert rows[0]["label"] == right
    assert rows[0]["predicted"] == record["item"]["code"]
    assert rows[0]["was_corrected"] == "true"
    assert "privada" not in text and "user" not in text.splitlines()[0]  # sin datos del usuario


def test_only_corrected_leaves_out_the_confirmations(
    client: TestClient, seeded: FastAPI, tmp_path: Path
) -> None:
    headers = auth_headers(client)
    confirmed = classify(client, headers, JPEG, "a.jpg", "image/jpeg")
    corrected = classify(client, headers, PNG, "b.png", "image/png")
    label(client, headers, confirmed["id"], confirmed["item"]["code"])
    label(
        client,
        headers,
        corrected["id"],
        next(i.code for i in ITEMS if i.code != corrected["item"]["code"]),
    )

    summary = export(seeded, tmp_path / "out", only_corrected=True)

    assert summary.exported == 1


def test_a_record_whose_file_is_gone_is_skipped_and_counted(
    client: TestClient, seeded: FastAPI, tmp_path: Path
) -> None:
    headers = auth_headers(client)
    record = classify(client, headers, JPEG, "a.jpg", "image/jpeg")
    label(client, headers, record["id"], "botella_pet")
    for file in Path(seeded.state.settings.storage_dir).rglob("*.jpg"):
        file.unlink()

    summary = export(seeded, tmp_path / "out")

    assert (summary.exported, summary.skipped_missing_file) == (0, 1)


def test_an_empty_export_still_writes_a_manifest(
    client: TestClient, seeded: FastAPI, tmp_path: Path
) -> None:
    export(seeded, tmp_path / "out")

    assert (tmp_path / "out" / MANIFEST).read_text(encoding="utf-8").startswith("id,file,label")
