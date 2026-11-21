"""Almacén de imágenes en disco (adaptador del puerto ``ImageStorage``).

En producción lo reemplaza un almacén compatible con S3 (Cloudflare R2 / MinIO, SAD §3.4) sin
tocar los casos de uso."""

from pathlib import Path


class LocalImageStorage:
    def __init__(self, root: Path) -> None:
        self._root = root.resolve()

    def save(self, key: str, data: bytes) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def read(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)

    def path_of(self, key: str) -> Path:
        """Ruta en disco de una clave (para exportar el dataset); rechaza claves inválidas."""
        return self._path(key)

    def _path(self, key: str) -> Path:
        """Clave → ruta, rechazando todo intento de salirse de la carpeta raíz."""
        parts = key.split("/")
        if (
            not key
            or key.startswith("/")
            or "\\" in key
            or ":" in key
            or any(p in ("", ".", "..") for p in parts)
        ):
            raise ValueError("clave de almacenamiento inválida")
        path = (self._root / key).resolve()
        if self._root not in path.parents:
            raise ValueError("clave de almacenamiento inválida")
        return path
