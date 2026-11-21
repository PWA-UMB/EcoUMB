"""Clasificador REAL (Sprint 3): MobileNetV3-Small exportado a ONNX en ``ml/`` (SAD §7).

Cumple el puerto ``ImageClassifier`` como el simulado: casos de uso, rutas y frontend no cambian.
El preprocesado replica el del entrenamiento (``ml/src/common.py::eval_transform``): lado corto a
256 px, recorte central de 224 y normalización de ImageNet, con NumPy y Pillow (sin PyTorch).

El modelo predice *materiales* (``labels.json``); ``class_map.json`` indica qué objeto del catálogo
UMB representa cada uno. La bolsa la decide la base de datos, no el modelo.
"""

import io
import json
from collections.abc import Sequence
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image, UnidentifiedImageError

from app.domain.entities.classification import Candidate, ModelInfo, Prediction, WasteItem
from app.domain.errors import CatalogUnavailable, InvalidImage

IMG_SIZE = 224
RESIZE = 256
MEAN = np.array((0.485, 0.456, 0.406), dtype=np.float32)
STD = np.array((0.229, 0.224, 0.225), dtype=np.float32)
TOP_K = 3
MODEL_FILE = "model.onnx"
INFERENCE_FILE = "inference.json"  # opcional: {"views": ["center", "flip"]}
VIEWS = ("center", "flip", "full")


def preprocess(image: Image.Image) -> np.ndarray:
    """Imagen → tensor float32 (3, 224, 224), idéntico al ``eval_transform`` del entrenamiento."""
    image = image.convert("RGB")
    width, height = image.size
    short, long_ = (width, height) if width <= height else (height, width)
    new_long = int(RESIZE * long_ / short)
    size = (RESIZE, new_long) if width <= height else (new_long, RESIZE)
    image = image.resize(size, Image.Resampling.BILINEAR)
    left = round((size[0] - IMG_SIZE) / 2.0)
    top = round((size[1] - IMG_SIZE) / 2.0)
    image = image.crop((left, top, left + IMG_SIZE, top + IMG_SIZE))
    array = np.asarray(image, dtype=np.float32) / 255.0
    return ((array - MEAN) / STD).transpose(2, 0, 1)


def _normalize(image: Image.Image) -> np.ndarray:
    array = np.asarray(image, dtype=np.float32) / 255.0
    return ((array - MEAN) / STD).transpose(2, 0, 1)


def preprocess_views(image: Image.Image, views: Sequence[str]) -> np.ndarray:
    """Lote (n, 3, 224, 224) con las vistas pedidas de una misma foto (promediarlas reduce errores).

    ``center``: el recorte de siempre · ``flip``: ese recorte espejado · ``full``: la foto completa
    (sin recortar) a 224 × 224, útil cuando el objeto queda cerca de un borde.
    """
    center = preprocess(image)
    out = []
    for view in views:
        if view == "flip":
            out.append(np.ascontiguousarray(center[:, :, ::-1]))
        elif view == "full":
            squashed = image.convert("RGB").resize((IMG_SIZE, IMG_SIZE), Image.Resampling.BILINEAR)
            out.append(_normalize(squashed))
        else:
            out.append(center)
    return np.stack(out).astype(np.float32)


def softmax(logits: np.ndarray) -> np.ndarray:
    """Softmax por filas (una por vista)."""
    exp = np.exp(logits - logits.max(axis=-1, keepdims=True))
    probabilities: np.ndarray = exp / exp.sum(axis=-1, keepdims=True)
    return probabilities


class OnnxClassifier:
    def __init__(self, model_dir: Path) -> None:
        model_path = model_dir / MODEL_FILE
        if not model_path.is_file():
            raise FileNotFoundError(f"No se encontró el modelo ONNX en {model_path}")
        self._labels: list[str] = json.loads((model_dir / "labels.json").read_text("utf-8"))
        self._class_map: dict[str, dict[str, str]] = json.loads(
            (model_dir / "class_map.json").read_text("utf-8")
        )
        missing = [label for label in self._labels if label not in self._class_map]
        if missing:
            raise ValueError(f"class_map.json no cubre las clases: {missing}")
        self._session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
        self._views = self._read_views(model_dir)
        self.info = self._read_info(model_dir)

    @staticmethod
    def _read_views(model_dir: Path) -> tuple[str, ...]:
        config = model_dir / INFERENCE_FILE
        views = (
            tuple(json.loads(config.read_text("utf-8")).get("views", ("center",)))
            if config.is_file()
            else ("center",)
        )
        unknown = [view for view in views if view not in VIEWS]
        if not views or unknown:
            raise ValueError(
                f"{INFERENCE_FILE}: vistas no válidas {unknown or views}; usa {list(VIEWS)}"
            )
        return views

    @staticmethod
    def _read_info(model_dir: Path) -> ModelInfo:
        metrics_file = model_dir / "metrics.json"
        metrics = json.loads(metrics_file.read_text("utf-8")) if metrics_file.is_file() else {}
        test = metrics.get("test", {})
        per_class = test.get("per_class", {})
        return ModelInfo(
            version=model_dir.name,
            path=f"{model_dir.name}/{MODEL_FILE}",
            accuracy=test.get("accuracy_top1"),
            f1_per_class={name: values["f1-score"] for name, values in per_class.items()} or None,
        )

    def predict(self, image: bytes, items: Sequence[WasteItem]) -> Prediction:
        batch = self._load(image)
        logits = self._session.run(None, {"image": batch})[0]
        probabilities = softmax(logits).mean(axis=0)  # promedio de las vistas
        by_code = {item.code: item for item in items}
        ranked = [
            (float(probability), by_code[self._class_map[label]["item_code"]])
            for label, probability in zip(self._labels, probabilities, strict=True)
            if self._class_map[label]["item_code"] in by_code
        ]
        if not ranked:
            raise CatalogUnavailable
        ranked.sort(key=lambda pair: pair[0], reverse=True)
        top = ranked[:TOP_K]
        return Prediction(
            item_id=top[0][1].id,
            confidence=round(top[0][0], 4),
            top3=tuple(Candidate(item.id, round(probability, 4)) for probability, item in top),
            model=self.info,
        )

    def _load(self, data: bytes) -> np.ndarray:
        try:
            with Image.open(io.BytesIO(data)) as image:
                image.load()
                return preprocess_views(image, self._views)
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
            raise InvalidImage("La imagen no se pudo decodificar.") from error
