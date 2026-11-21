"""Constantes y utilidades compartidas por el entrenamiento y la evaluación (v1: TrashNet; v2: + RealWaste)."""

import hashlib
import json
import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from sklearn.model_selection import train_test_split
from torchvision import transforms

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
TRASHNET_ZIP = RAW / "dataset-resized.zip"
REALWASTE_ZIP = RAW / "realwaste.zip"
TRASHNET_DIR = RAW / "dataset-resized"
REALWASTE_DIR = RAW / "realwaste" / "realwaste-main" / "RealWaste"
MODELS_DIR = ROOT / "models"

SEED = 42
IMG_SIZE = 224
RESIZE = 256
MEAN = (0.485, 0.456, 0.406)  # normalización de ImageNet: el modelo base se preentrenó con ella
STD = (0.229, 0.224, 0.225)
TRAIN_SHARE, VAL_SHARE = 0.70, 0.15  # el 15 % restante es test (SAD §7.3)

CLASSES_V1 = ["cardboard", "glass", "metal", "paper", "plastic", "trash"]
CLASSES_V2 = [*CLASSES_V1, "organic_food", "vegetation"]  # los seis primeros conservan su índice

# Cada clase del modelo se asocia con el objeto del catálogo UMB que mejor la representa (provisional;
# se puede editar sin reentrenar). La bolsa la decide la base de datos.
CLASS_MAP: dict[str, dict[str, str]] = {
    "cardboard": {"item_code": "carton_limpio", "category": "aprovechable"},
    "glass": {"item_code": "botella_vidrio", "category": "aprovechable"},
    "metal": {"item_code": "lata_aluminio", "category": "aprovechable"},
    "paper": {"item_code": "papel_limpio", "category": "aprovechable"},
    "plastic": {"item_code": "botella_pet", "category": "aprovechable"},
    "trash": {"item_code": "empaque_comida_residuos", "category": "no_aprovechable"},
    "organic_food": {"item_code": "restos_comida", "category": "organico"},
    "vegetation": {"item_code": "residuo_poda", "category": "organico"},
}

# Carpeta de RealWaste → clase del modelo (la ropa desechada va con la basura general).
REALWASTE_TO_CLASS = {
    "Cardboard": "cardboard",
    "Food Organics": "organic_food",
    "Glass": "glass",
    "Metal": "metal",
    "Miscellaneous Trash": "trash",
    "Paper": "paper",
    "Plastic": "plastic",
    "Textile Trash": "trash",
    "Vegetation": "vegetation",
}


@dataclass(frozen=True)
class DatasetSpec:
    name: str
    classes: list[str]
    sources: tuple[str, ...]
    splits_file: Path


DATASETS = {
    "trashnet": DatasetSpec("trashnet", CLASSES_V1, ("trashnet",), ROOT / "data" / "splits.json"),
    "combined": DatasetSpec(
        "combined", CLASSES_V2, ("trashnet", "realwaste"), ROOT / "data" / "splits_combined.json"
    ),
}


def out_dir(version: str) -> Path:
    return MODELS_DIR / version


def seed_everything(seed: int = SEED) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


# --- rutas: TrashNet va sin prefijo (igual que en v1); RealWaste con el prefijo «realwaste/» ---
def image_path(relative: str) -> Path:
    if relative.startswith("realwaste/"):
        return REALWASTE_DIR / relative[len("realwaste/") :]
    return TRASHNET_DIR / relative


def source_of(relative: str) -> str:
    return "realwaste" if relative.startswith("realwaste/") else "trashnet"


def list_images(spec: DatasetSpec) -> tuple[list[str], list[int]]:
    paths: list[str] = []
    labels: list[int] = []
    if "trashnet" in spec.sources:
        for name in CLASSES_V1:
            for file in sorted((TRASHNET_DIR / name).glob("*.jpg")):
                paths.append(f"{name}/{file.name}")
                labels.append(spec.classes.index(name))
    if "realwaste" in spec.sources:
        for folder, name in REALWASTE_TO_CLASS.items():
            for file in sorted((REALWASTE_DIR / folder).glob("*.jpg")):
                paths.append(f"realwaste/{folder}/{file.name}")
                labels.append(spec.classes.index(name))
    return paths, labels


def make_splits(spec: DatasetSpec) -> dict[str, list[tuple[str, int]]]:
    """70/15/15 estratificado por fuente y clase, con semilla fija. Una foto está en un solo conjunto."""
    paths, labels = list_images(spec)
    strata = [f"{source_of(p)}:{label}" for p, label in zip(paths, labels, strict=True)]
    train_x, rest_x, train_y, rest_y, _, rest_s = train_test_split(
        paths, labels, strata, train_size=TRAIN_SHARE, stratify=strata, random_state=SEED
    )
    val_size = VAL_SHARE / (1 - TRAIN_SHARE)
    val_x, test_x, val_y, test_y = train_test_split(
        rest_x, rest_y, train_size=val_size, stratify=rest_s, random_state=SEED
    )
    splits = {
        "train": list(zip(train_x, train_y, strict=True)),
        "val": list(zip(val_x, val_y, strict=True)),
        "test": list(zip(test_x, test_y, strict=True)),
    }
    spec.splits_file.write_text(json.dumps(splits, indent=1), encoding="utf-8")
    return splits


def train_transform(robust: bool = False, donors: list[Image.Image] | None = None) -> transforms.Compose:
    """``robust`` añade los aumentos de campo de ``augment.py`` (fondos, oclusiones, matiz, grises)."""
    if robust:
        from augment import RandomBackground, RandomOcclusion

        return transforms.Compose(
            [
                RandomBackground(p=0.7, donors=donors),
                RandomOcclusion(p=0.5),
                transforms.RandomResizedCrop(IMG_SIZE, scale=(0.4, 1.0)),
                transforms.RandomHorizontalFlip(),
                transforms.RandomRotation(25),
                transforms.ColorJitter(brightness=0.4, contrast=0.4, saturation=0.5, hue=0.5),
                transforms.RandomGrayscale(p=0.15),
                transforms.RandomApply([transforms.GaussianBlur(5, (0.1, 1.5))], p=0.2),
                transforms.ToTensor(),
                transforms.Normalize(MEAN, STD),
                transforms.RandomErasing(p=0.25, scale=(0.02, 0.15)),
            ]
        )
    return transforms.Compose(
        [
            transforms.RandomResizedCrop(IMG_SIZE, scale=(0.6, 1.0)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomRotation(20),
            transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.3, hue=0.05),
            transforms.ToTensor(),
            transforms.Normalize(MEAN, STD),
        ]
    )


def train_transforms_by_source(
    robust: bool, donors: list[Image.Image] | None
) -> dict[str, transforms.Compose]:
    """Fondos aleatorios solo para TrashNet (fondo blanco, fácil de recortar); RealWaste ya trae fondo real,
    pero recibe el resto de los aumentos de campo (matiz, oclusiones, desenfoque)."""
    if not robust:
        plain = train_transform(False)
        return {"trashnet": plain, "realwaste": plain}
    with_background = train_transform(True, donors)
    without_background = transforms.Compose(
        [t for t in with_background.transforms if type(t).__name__ != "RandomBackground"]
    )
    return {"trashnet": with_background, "realwaste": without_background}


def load_donors(train_items: list[tuple[str, int]], count: int = 60) -> list[Image.Image]:
    """Fotos pequeñas de entrenamiento que sirven de fondo (borroso) en RandomBackground."""
    rng = random.Random(SEED)
    donors = []
    for relative, _ in rng.sample(train_items, count):
        with Image.open(image_path(relative)) as image:
            donors.append(image.convert("RGB").resize((256, 192)))
    return donors


def eval_transform() -> transforms.Compose:
    return transforms.Compose(
        [
            transforms.Resize(RESIZE),
            transforms.CenterCrop(IMG_SIZE),
            transforms.ToTensor(),
            transforms.Normalize(MEAN, STD),
        ]
    )


class ImageDataset(torch.utils.data.Dataset):
    """Fotos con su etiqueta; cada fuente puede tener su propia transformación."""

    def __init__(
        self,
        items: list[tuple[str, int]],
        transform: transforms.Compose | dict[str, transforms.Compose],
    ) -> None:
        self.items = items
        self.transform = transform

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, int]:
        relative, label = self.items[index]
        transform = (
            self.transform[source_of(relative)] if isinstance(self.transform, dict) else self.transform
        )
        with Image.open(image_path(relative)) as image:
            return transform(image.convert("RGB")), label
