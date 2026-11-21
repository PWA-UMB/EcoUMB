from pathlib import Path

from app.core.config import Settings
from app.domain.ports import ImageClassifier
from app.infrastructure.ml_client.simulated import SimulatedClassifier


def build_classifier(settings: Settings) -> ImageClassifier:
    """Elige el clasificador por configuración; con ``onnx``, sin modelo la API no arranca."""
    if settings.classifier == "simulated":
        return SimulatedClassifier()
    if settings.classifier == "onnx":
        from app.infrastructure.ml_client.onnx import (
            OnnxClassifier,
        )  # carga onnxruntime solo si se usa

        return OnnxClassifier(Path(settings.model_dir))
    raise ValueError(f"CLASSIFIER inválido: {settings.classifier!r} (usa 'simulated' u 'onnx')")
