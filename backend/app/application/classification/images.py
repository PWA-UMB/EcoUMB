"""Validación de la imagen subida (RF-09, RF-10). Se decide por los primeros bytes, no por el nombre
ni por el ``Content-Type`` que declara el cliente, que se pueden falsificar."""

from dataclasses import dataclass

from app.domain.errors import EmptyImage, ImageTooLarge, UnsupportedImageType

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_JPEG_SIGNATURE = b"\xff\xd8\xff"

CONTENT_TYPE_BY_EXTENSION = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}


@dataclass(frozen=True)
class ValidatedImage:
    content_type: str
    extension: str


def validate_image(data: bytes, *, max_bytes: int) -> ValidatedImage:
    if not data:
        raise EmptyImage
    if len(data) > max_bytes:
        raise ImageTooLarge
    if data.startswith(_JPEG_SIGNATURE):
        return ValidatedImage("image/jpeg", "jpg")
    if data.startswith(_PNG_SIGNATURE):
        return ValidatedImage("image/png", "png")
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ValidatedImage("image/webp", "webp")
    raise UnsupportedImageType
