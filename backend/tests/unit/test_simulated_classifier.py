"""Clasificador simulado (Sprint 2): contrato del modelo real, resultados creíbles y estables."""

import uuid

import pytest

from app.domain.confidence import ConfidenceBand, band_for
from app.domain.entities.classification import WasteItem
from app.infrastructure.ml_client.simulated import SimulatedClassifier


def _items(n: int = 15) -> list[WasteItem]:
    return [
        WasteItem(
            id=uuid.uuid4(),
            class_id=i,
            code=f"item_{i}",
            display_name=f"Objeto {i}",
            category_code="aprovechable",
            bag_color="blanca",
            short_message="mensaje",
            disposal_tip="consejo",
            points_value=10,
        )
        for i in range(n)
    ]


@pytest.mark.parametrize(
    ("confidence", "band"),
    [
        (0.99, ConfidenceBand.HIGH),
        (0.85, ConfidenceBand.HIGH),  # el umbral alto es inclusivo (SAD §7.5)
        (0.8499, ConfidenceBand.MEDIUM),
        (0.65, ConfidenceBand.MEDIUM),  # el umbral medio es inclusivo
        (0.6499, ConfidenceBand.LOW),
        (0.0, ConfidenceBand.LOW),
    ],
)
def test_confidence_bands_follow_the_sad_thresholds(
    confidence: float, band: ConfidenceBand
) -> None:
    assert band_for(confidence) is band


def test_same_image_always_gets_the_same_answer() -> None:
    items, classifier = _items(), SimulatedClassifier()

    first = classifier.predict(b"foto-de-una-botella", items)
    second = classifier.predict(b"foto-de-una-botella", items)

    assert first == second


def test_different_images_can_get_different_answers() -> None:
    items, classifier = _items(), SimulatedClassifier()

    chosen = {classifier.predict(f"foto-{n}".encode(), items).item_id for n in range(40)}

    assert len(chosen) > 3  # no responde siempre lo mismo


def test_prediction_is_a_valid_top3_over_the_catalog() -> None:
    items, classifier = _items(), SimulatedClassifier()
    ids = {item.id for item in items}

    for n in range(60):
        prediction = classifier.predict(f"imagen-{n}".encode(), items)

        assert prediction.item_id in ids
        assert 0.0 < prediction.confidence < 1.0
        assert len(prediction.top3) == 3
        assert prediction.top3[0].item_id == prediction.item_id
        assert prediction.top3[0].confidence == prediction.confidence
        assert len({c.item_id for c in prediction.top3}) == 3  # candidatos distintos
        scores = [c.confidence for c in prediction.top3]
        assert scores == sorted(scores, reverse=True)  # de mayor a menor
        assert sum(scores) <= 1.0001  # probabilidades coherentes


def test_all_three_confidence_bands_occur() -> None:
    items, classifier = _items(), SimulatedClassifier()

    bands = {band_for(classifier.predict(f"x{n}".encode(), items).confidence) for n in range(200)}

    assert bands == {ConfidenceBand.HIGH, ConfidenceBand.MEDIUM, ConfidenceBand.LOW}


def test_works_with_a_tiny_catalog() -> None:
    items = _items(3)

    prediction = SimulatedClassifier().predict(b"abc", items)

    assert len(prediction.top3) == 3
