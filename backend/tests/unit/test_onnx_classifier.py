"""Clasificador ONNX (Sprint 3): preprocesado, ranking y errores, con un modelo diminuto."""

import io
import json
import uuid
from pathlib import Path

import numpy as np
import onnx
import pytest
from onnx import TensorProto, helper, numpy_helper
from PIL import Image

from app.core.config import Settings
from app.domain.entities.classification import WasteItem
from app.domain.errors import CatalogUnavailable, InvalidImage
from app.infrastructure.ml_client.factory import build_classifier
from app.infrastructure.ml_client.onnx import (
    IMG_SIZE,
    MEAN,
    STD,
    OnnxClassifier,
    preprocess,
    preprocess_views,
)
from app.infrastructure.ml_client.simulated import SimulatedClassifier

LABELS = ["cardboard", "glass", "metal"]  # canal R → cartón, G → vidrio, B → metal
CODES = {"cardboard": "carton_limpio", "glass": "botella_vidrio", "metal": "lata_aluminio"}


def build_tiny_model(path: Path) -> None:
    """logits = media de cada canal × 10: rojo → cartón, verde → vidrio, azul → metal."""
    weights = numpy_helper.from_array((np.eye(3) * 10).astype(np.float32), name="weights")
    graph = helper.make_graph(
        [
            helper.make_node("ReduceMean", ["image"], ["means"], axes=[2, 3], keepdims=0),
            helper.make_node("MatMul", ["means", "weights"], ["logits"]),
        ],
        "tiny",
        [
            helper.make_tensor_value_info(
                "image", TensorProto.FLOAT, ["batch", 3, IMG_SIZE, IMG_SIZE]
            )
        ],
        [helper.make_tensor_value_info("logits", TensorProto.FLOAT, ["batch", 3])],
        [weights],
    )
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])
    model.ir_version = 8  # el más antiguo que onnxruntime siempre entiende
    onnx.save(model, str(path))


@pytest.fixture
def model_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "v9"
    directory.mkdir()
    build_tiny_model(directory / "model.onnx")
    (directory / "labels.json").write_text(json.dumps(LABELS), encoding="utf-8")
    class_map = {label: {"item_code": CODES[label], "category": "aprovechable"} for label in LABELS}
    (directory / "class_map.json").write_text(json.dumps(class_map), encoding="utf-8")
    metrics = {"test": {"accuracy_top1": 0.9, "per_class": {"glass": {"f1-score": 0.8}}}}
    (directory / "metrics.json").write_text(json.dumps(metrics), encoding="utf-8")
    return directory


def make_settings(classifier: str = "simulated", model_dir: str = "") -> Settings:
    return Settings(app_env="test", classifier=classifier, model_dir=model_dir, _env_file=None)


def catalog(codes: list[str] | None = None) -> list[WasteItem]:
    return [
        WasteItem(uuid.uuid4(), n, code, code, "aprovechable", "blanca", "m", "t", 1)
        for n, code in enumerate(codes or list(CODES.values()) + ["botella_pet", "papel_limpio"])
    ]


def png(color: tuple[int, int, int], size: tuple[int, int] = (320, 240)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format="PNG")
    return buffer.getvalue()


# ------------------------------------------------------------------ preprocesamiento
def test_preprocess_returns_a_normalized_224_tensor() -> None:
    tensor = preprocess(Image.new("RGB", (640, 480), (255, 255, 255)))

    assert tensor.shape == (3, IMG_SIZE, IMG_SIZE)
    assert tensor.dtype == np.float32
    expected = (1.0 - MEAN) / STD  # blanco puro tras la normalización de ImageNet
    assert np.allclose(tensor, expected[:, None, None], atol=1e-5)  # todos los píxeles


def test_preprocess_center_crops_after_resizing_the_short_side() -> None:
    wide = Image.new(
        "RGB", (512, 256), (255, 255, 255)
    )  # se reduce a 256 de alto, sin cambio de ancho
    for x in range(0, 100):  # franja negra a la izquierda, fuera del recorte central de 224 px
        for y in range(256):
            wide.putpixel((x, y), (0, 0, 0))

    tensor = preprocess(wide)

    assert np.allclose(tensor, ((1.0 - MEAN) / STD)[:, None, None], atol=1e-5)


@pytest.mark.parametrize("mode", ["L", "RGBA", "P"])
def test_preprocess_accepts_other_color_modes(mode: str) -> None:
    assert preprocess(Image.new(mode, (300, 300))).shape == (3, IMG_SIZE, IMG_SIZE)


# ------------------------------------------------------------------------ predicción
@pytest.mark.parametrize(
    ("color", "expected"),
    [
        ((255, 0, 0), "carton_limpio"),
        ((0, 255, 0), "botella_vidrio"),
        ((0, 0, 255), "lata_aluminio"),
    ],
)
def test_the_prediction_follows_the_image_content(
    model_dir: Path, color: tuple[int, int, int], expected: str
) -> None:
    items = catalog()
    prediction = OnnxClassifier(model_dir).predict(png(color), items)

    by_id = {item.id: item.code for item in items}
    assert by_id[prediction.item_id] == expected


def test_top3_is_sorted_and_starts_with_the_best_item(model_dir: Path) -> None:
    prediction = OnnxClassifier(model_dir).predict(png((255, 0, 0)), catalog())

    confidences = [c.confidence for c in prediction.top3]
    assert len(prediction.top3) == 3
    assert confidences == sorted(confidences, reverse=True)
    assert prediction.top3[0].item_id == prediction.item_id
    assert prediction.confidence == confidences[0]
    assert 0 < sum(confidences) <= 1.0001  # son probabilidades (softmax)


def test_the_prediction_carries_the_model_version_and_its_metrics(model_dir: Path) -> None:
    prediction = OnnxClassifier(model_dir).predict(png((0, 255, 0)), catalog())

    assert prediction.model is not None
    assert prediction.model.version == "v9"
    assert prediction.model.accuracy == 0.9
    assert prediction.model.f1_per_class == {"glass": 0.8}


def test_classes_missing_from_the_catalog_are_left_out(model_dir: Path) -> None:
    items = catalog(["carton_limpio", "lata_aluminio"])  # sin botella_vidrio

    prediction = OnnxClassifier(model_dir).predict(png((0, 255, 0)), items)

    assert {c.item_id for c in prediction.top3} <= {item.id for item in items}
    assert len(prediction.top3) == 2


def test_an_empty_catalog_is_reported(model_dir: Path) -> None:
    with pytest.raises(CatalogUnavailable):
        OnnxClassifier(model_dir).predict(png((255, 0, 0)), catalog(["botella_pet"]))


def test_bytes_that_are_not_an_image_are_rejected(model_dir: Path) -> None:
    corrupt = b"\xff\xd8\xff\xe0" + b"no es una imagen jpeg de verdad" * 4

    with pytest.raises(InvalidImage):
        OnnxClassifier(model_dir).predict(corrupt, catalog())


# ------------------------------------------------------------------------- arranque
def test_a_missing_model_stops_the_start(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="model.onnx"):
        OnnxClassifier(tmp_path)


def test_an_incomplete_class_map_stops_the_start(model_dir: Path) -> None:
    (model_dir / "class_map.json").write_text(json.dumps({"glass": {}}), encoding="utf-8")

    with pytest.raises(ValueError, match="class_map.json"):
        OnnxClassifier(model_dir)


def test_metrics_are_optional(model_dir: Path) -> None:
    (model_dir / "metrics.json").unlink()

    info = OnnxClassifier(model_dir).info

    assert info.version == "v9"
    assert info.accuracy is None
    assert info.f1_per_class is None


def test_the_factory_picks_the_classifier_from_settings(model_dir: Path) -> None:
    assert isinstance(build_classifier(make_settings()), SimulatedClassifier)
    onnx_settings = make_settings(classifier="onnx", model_dir=str(model_dir))
    assert isinstance(build_classifier(onnx_settings), OnnxClassifier)
    with pytest.raises(ValueError, match="CLASSIFIER"):
        build_classifier(make_settings(classifier="magia"))
    with pytest.raises(FileNotFoundError):
        build_classifier(make_settings(classifier="onnx", model_dir=str(model_dir / "x")))


# ------------------------------------------------------------------ varias vistas de la foto
def left_red_right_blue() -> Image.Image:
    image = Image.new("RGB", (300, 300), (0, 0, 255))
    for x in range(150):
        for y in range(300):
            image.putpixel((x, y), (255, 0, 0))
    return image


def test_views_are_stacked_in_the_requested_order() -> None:
    batch = preprocess_views(left_red_right_blue(), ["center", "flip", "full"])

    assert batch.shape == (3, 3, IMG_SIZE, IMG_SIZE)
    assert batch.dtype == np.float32


def test_the_flip_view_is_the_mirror_of_the_center_view() -> None:
    image = left_red_right_blue()
    center, flipped = preprocess_views(image, ["center", "flip"])

    assert np.allclose(flipped, center[:, :, ::-1])
    assert not np.allclose(flipped, center)  # la foto es asimétrica: el espejo cambia algo


def test_the_full_view_keeps_the_borders_that_the_crop_discards() -> None:
    wide = Image.new("RGB", (600, 200), (255, 255, 255))
    for x in range(40):  # franja negra en el borde izquierdo: el recorte central la descarta
        for y in range(200):
            wide.putpixel((x, y), (0, 0, 0))

    center, full = preprocess_views(wide, ["center", "full"])

    assert center.min() > full.min()  # solo la vista completa ve la franja negra


def test_the_default_is_a_single_center_view(model_dir: Path) -> None:
    classifier = OnnxClassifier(model_dir)

    assert classifier._views == ("center",)  # noqa: SLF001


def test_inference_json_can_average_several_views(model_dir: Path) -> None:
    (model_dir / "inference.json").write_text(
        json.dumps({"views": ["center", "flip", "full"]}), encoding="utf-8"
    )
    items = catalog()

    prediction = OnnxClassifier(model_dir).predict(png((255, 0, 0)), items)

    by_id = {item.id: item.code for item in items}
    assert by_id[prediction.item_id] == "carton_limpio"
    assert prediction.confidence == max(c.confidence for c in prediction.top3)


def test_averaging_views_changes_the_confidence_when_the_views_disagree(model_dir: Path) -> None:
    """La vista completa ve el tercio izquierdo que el recorte central descarta.

    Los colores son casi grises a propósito: el modelo de prueba amplifica ×10 y con colores
    saturados la confianza sería 1,0 en todas las vistas y no se notaría la diferencia.
    """
    wide = Image.new("RGB", (900, 300), (128, 132, 128))
    for x in range(300):
        for y in range(300):
            wide.putpixel((x, y), (140, 100, 100))
    buffer = io.BytesIO()
    wide.save(buffer, format="PNG")
    items = catalog()
    single = OnnxClassifier(model_dir).predict(buffer.getvalue(), items)
    (model_dir / "inference.json").write_text(json.dumps({"views": ["center", "full"]}), "utf-8")

    averaged = OnnxClassifier(model_dir).predict(buffer.getvalue(), items)

    assert averaged.confidence != single.confidence


@pytest.mark.parametrize("views", [[], ["zoom"], ["center", "zoom"]])
def test_invalid_views_stop_the_start(model_dir: Path, views: list[str]) -> None:
    (model_dir / "inference.json").write_text(json.dumps({"views": views}), encoding="utf-8")

    with pytest.raises(ValueError, match="inference.json"):
        OnnxClassifier(model_dir)
