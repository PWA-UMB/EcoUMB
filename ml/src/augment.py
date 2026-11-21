"""Aumentos «de campo» para el modelo v1.1: rompen los atajos que TrashNet permite.

TrashNet son objetos sueltos sobre fondo blanco. Un modelo entrenado solo con eso aprende «fondo blanco +
color» (p. ej. verde = vidrio) y falla con una lata en la mano frente a una habitación. Estas transformaciones
obligan a fijarse en la forma y la textura del objeto:

- ``RandomBackground``: recorta el objeto (todo lo que difiere del fondo) y lo pega, con otra escala y posición,
  sobre fondos aleatorios (color liso, degradado, ruido, o un fragmento borroso de otra foto).
- ``RandomOcclusion``: manchas de tono piel/oscuras que tapan parte del objeto, como una mano o un cuerpo.
- Cambios fuertes de matiz y escala de grises, que quitan la dependencia del color.
"""

import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

CANVAS = 256
MIN_OBJECT_SHARE = 0.10  # por debajo, el objeto es casi del color del fondo (p. ej. papel blanco)
MAX_OBJECT_SHARE = 0.97
BACKGROUND_DISTANCE = 30  # distancia de color al fondo a partir de la cual un píxel es «objeto»
SKIN_TONES = [(224, 172, 140), (198, 134, 102), (141, 85, 60), (241, 194, 160)]


def object_mask(image: Image.Image) -> Image.Image:
    """Máscara del objeto: píxeles que se alejan del color de fondo (mediana del borde de la foto)."""
    array = np.asarray(image.convert("RGB"), dtype=np.float32)
    border = np.concatenate([array[0], array[-1], array[:, 0], array[:, -1]])
    background = np.median(border, axis=0)
    distance = np.linalg.norm(array - background, axis=2)
    mask = Image.fromarray(((distance > BACKGROUND_DISTANCE) * 255).astype(np.uint8))
    mask = mask.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(5))  # cierra huecos
    return mask.filter(ImageFilter.GaussianBlur(1.5))


def random_background(rng: object, donors: list[Image.Image]) -> Image.Image:
    kind = rng.choice(["solid", "gradient", "noise", "photo"] if donors else ["solid", "gradient", "noise"])
    if kind == "solid":
        return Image.new("RGB", (CANVAS, CANVAS), tuple(rng.randrange(256) for _ in range(3)))
    if kind == "gradient":
        top, bottom = (np.array([rng.randrange(256) for _ in range(3)], dtype=np.float32) for _ in range(2))
        ramp = np.linspace(0, 1, CANVAS, dtype=np.float32)[:, None, None]
        data = (top * (1 - ramp) + bottom * ramp) * np.ones((CANVAS, CANVAS, 3), dtype=np.float32)
        return Image.fromarray(data.astype(np.uint8))
    if kind == "noise":
        seed = rng.randrange(1 << 30)
        base = np.random.default_rng(seed).integers(40, 216, (6, 6, 3), dtype=np.uint8)
        return Image.fromarray(base).resize((CANVAS, CANVAS), Image.Resampling.BICUBIC)
    donor = rng.choice(donors)
    left = rng.randrange(0, max(1, donor.width - 128))
    top = rng.randrange(0, max(1, donor.height - 128))
    patch = donor.crop((left, top, left + 128, top + 128)).resize((CANVAS, CANVAS))
    return patch.filter(ImageFilter.GaussianBlur(4))


class RandomBackground:
    """Con probabilidad ``p`` pega el objeto sobre un fondo aleatorio, a escala y posición aleatorias."""

    def __init__(self, p: float = 0.7, donors: list[Image.Image] | None = None) -> None:
        self.p = p
        self.donors = donors or []

    def __call__(self, image: Image.Image) -> Image.Image:
        rng = random  # generador global: reproducible con random.seed() y por worker
        if rng.random() > self.p:
            return image
        image = image.convert("RGB")
        mask = object_mask(image)
        box = mask.getbbox()
        share = float(np.asarray(mask).mean()) / 255.0
        if box is None or not MIN_OBJECT_SHARE <= share <= MAX_OBJECT_SHARE:
            return image  # no se pudo separar el objeto del fondo: se deja la foto original
        obj, obj_mask = image.crop(box), mask.crop(box)
        scale = rng.uniform(0.45, 1.0) * CANVAS / max(obj.size)
        size = (max(8, int(obj.width * scale)), max(8, int(obj.height * scale)))
        obj, obj_mask = obj.resize(size), obj_mask.resize(size)
        canvas = random_background(rng, self.donors)
        x = rng.randrange(0, max(1, CANVAS - size[0]) + 1)
        y = rng.randrange(0, max(1, CANVAS - size[1]) + 1)
        canvas.paste(obj, (x, y), obj_mask)
        return canvas


class RandomOcclusion:
    """Manchas tipo mano o cuerpo que tapan parte de la imagen."""

    def __init__(self, p: float = 0.5) -> None:
        self.p = p

    def __call__(self, image: Image.Image) -> Image.Image:
        rng = random  # generador global: reproducible con random.seed() y por worker
        if rng.random() > self.p:
            return image
        image = image.convert("RGB").copy()
        draw = ImageDraw.Draw(image)
        width, height = image.size
        for _ in range(rng.randint(1, 2)):
            color = rng.choice(SKIN_TONES + [(40, 40, 45), (110, 110, 115)])
            w, h = int(width * rng.uniform(0.15, 0.4)), int(height * rng.uniform(0.2, 0.5))
            x, y = rng.randrange(0, width - w), rng.randrange(0, height - h)
            draw.ellipse((x, y, x + w, y + h), fill=color)
        return image
