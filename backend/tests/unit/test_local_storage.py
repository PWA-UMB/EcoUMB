"""Almacén local de imágenes (puerto ImageStorage); en producción, R2/MinIO (SAD §3.4)."""

from pathlib import Path

import pytest

from app.infrastructure.storage.local import LocalImageStorage


def test_saves_and_reads_back(tmp_path: Path) -> None:
    storage = LocalImageStorage(tmp_path)

    storage.save("user-1/a.jpg", b"contenido")

    assert storage.read("user-1/a.jpg") == b"contenido"
    assert (tmp_path / "user-1" / "a.jpg").exists()


def test_reading_a_missing_key_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        LocalImageStorage(tmp_path).read("no/existe.jpg")


def test_delete_removes_the_file_and_is_idempotent(tmp_path: Path) -> None:
    storage = LocalImageStorage(tmp_path)
    storage.save("u/a.png", b"x")

    storage.delete("u/a.png")
    storage.delete("u/a.png")  # no falla si ya no está

    assert not (tmp_path / "u" / "a.png").exists()


@pytest.mark.parametrize(
    "key", ["../fuera.jpg", "a/../../fuera.jpg", "/etc/passwd", "C:/Windows/x.jpg", "a\\..\\b.jpg"]
)
def test_keys_cannot_escape_the_storage_directory(tmp_path: Path, key: str) -> None:
    storage = LocalImageStorage(tmp_path / "raiz")

    with pytest.raises(ValueError, match="clave"):
        storage.save(key, b"x")
    with pytest.raises(ValueError, match="clave"):
        storage.read(key)
