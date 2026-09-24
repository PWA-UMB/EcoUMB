"""RF-09 / RF-10: solo se aceptan imágenes reales, validadas por su contenido y no por su nombre."""

import pytest

from app.application.classification.images import ValidatedImage, validate_image
from app.domain.errors import EmptyImage, ImageTooLarge, UnsupportedImageType
from tests.conftest import JPEG, PNG, WEBP

LIMIT = 5 * 1024 * 1024


@pytest.mark.parametrize(
    ("data", "content_type", "extension"),
    [(JPEG, "image/jpeg", "jpg"), (PNG, "image/png", "png"), (WEBP, "image/webp", "webp")],
)
def test_valid_images_are_detected_by_their_bytes(
    data: bytes, content_type: str, extension: str
) -> None:
    assert validate_image(data, max_bytes=LIMIT) == ValidatedImage(content_type, extension)


@pytest.mark.parametrize(
    "data",
    [
        b"esto es texto, no una imagen",
        b"GIF89a" + b"\x00" * 20,
        b"%PDF-1.7" + b"\x00" * 20,
        b"<svg></svg>",
    ],
)
def test_other_formats_are_rejected(data: bytes) -> None:
    with pytest.raises(UnsupportedImageType):
        validate_image(data, max_bytes=LIMIT)


def test_a_renamed_file_does_not_fool_the_validation() -> None:
    """El cliente puede decir que es image/jpeg; lo que cuenta son los primeros bytes."""
    with pytest.raises(UnsupportedImageType):
        validate_image(b"#!/bin/sh\nrm -rf /\n", max_bytes=LIMIT)


def test_empty_upload_is_rejected() -> None:
    with pytest.raises(EmptyImage):
        validate_image(b"", max_bytes=LIMIT)


def test_size_limit_is_enforced() -> None:
    with pytest.raises(ImageTooLarge):
        validate_image(JPEG + b"\x00" * 100, max_bytes=len(JPEG))


def test_image_exactly_at_the_limit_is_accepted() -> None:
    assert validate_image(JPEG, max_bytes=len(JPEG)).extension == "jpg"
