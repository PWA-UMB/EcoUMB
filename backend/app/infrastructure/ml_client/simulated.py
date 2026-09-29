"""Clasificador SIMULADO del Sprint 2 (Plan de Sprints: «endpoint de clasificación simulada»).

Cumple el mismo contrato que tendrá el modelo real (MobileNetV3, Sprint 3-4): el flujo completo
foto → resultado → registro se prueba hoy y el modelo se cambia después sin tocar el resto (RNF-17).

No mira los píxeles: deriva un resultado *determinista* del contenido de la imagen, así la misma
foto siempre recibe la misma respuesta (demostración creíble, pruebas repetibles). La API declara
``simulated: true``.
"""

import hashlib
import random
from collections.abc import Sequence

from app.domain.entities.classification import Candidate, Prediction, WasteItem

# Reparto de bandas de confianza (alta / media / baja) para que la interfaz muestre los tres casos.
_HIGH_SHARE, _MEDIUM_SHARE = 0.70, 0.20


class SimulatedClassifier:
    def predict(self, image: bytes, items: Sequence[WasteItem]) -> Prediction:
        seed = int.from_bytes(hashlib.sha256(image).digest()[:8], "big")
        rng = random.Random(seed)  # noqa: S311 - resultado simulado, no criptográfico

        pool = list(items)
        best = rng.choice(pool)
        roll = rng.random()
        if roll < _HIGH_SHARE:
            confidence = rng.uniform(0.86, 0.99)
        elif roll < _HIGH_SHARE + _MEDIUM_SHARE:
            confidence = rng.uniform(0.66, 0.84)
        else:
            confidence = rng.uniform(0.40, 0.64)
        confidence = round(confidence, 4)

        others = rng.sample([i for i in pool if i.id != best.id], k=min(2, len(pool) - 1))
        remaining = 1.0 - confidence
        second = round(min(remaining * 0.6, confidence * 0.9), 4)
        third = round(min(remaining - second, second * 0.8), 4)
        scores = [confidence, second, third]

        top3 = tuple(
            Candidate(item.id, score) for item, score in zip([best, *others], scores, strict=False)
        )
        return Prediction(item_id=best.id, confidence=confidence, top3=top3)
