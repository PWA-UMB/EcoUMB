"""Bandas de confianza de una predicción (SAD §7.5)."""

from enum import StrEnum

HIGH_THRESHOLD = 0.85  # softmax_max >= 0.85: se muestra el objeto directamente
MEDIUM_THRESHOLD = 0.65  # 0.65 <= softmax_max < 0.85: se piden candidatos al usuario


class ConfidenceBand(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


def band_for(confidence: float) -> ConfidenceBand:
    if confidence >= HIGH_THRESHOLD:
        return ConfidenceBand.HIGH
    if confidence >= MEDIUM_THRESHOLD:
        return ConfidenceBand.MEDIUM
    return ConfidenceBand.LOW
