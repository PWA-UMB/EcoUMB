"""Evalúa un modelo sobre el conjunto de TEST (una sola vez), lo exporta a ONNX y escribe sus métricas.

Uso (desde ml/):
  .venv/Scripts/python src/evaluate.py --version v2 --dataset combined
  .venv/Scripts/python src/evaluate.py --version v1 --dataset trashnet

Las métricas se calculan sobre el modelo ONNX con el mismo preprocesamiento que usa la API (NumPy + Pillow),
no sobre el de PyTorch: así lo que se reporta es lo que realmente se despliega.

Además, si existe ``ml/data/umb/<objeto>/*.jpg`` (fotos reales exportadas de la app o etiquetadas a mano),
se mide también sobre ellas y se listan una por una: son la única medición que se parece al uso real.
"""

import argparse
import json
import platform
import statistics
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import onnx  # noqa: E402
import onnxruntime as ort  # noqa: E402
import sklearn  # noqa: E402
import torch  # noqa: E402
import torchvision  # noqa: E402
from PIL import Image  # noqa: E402
from sklearn.metrics import (  # noqa: E402
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    roc_auc_score,
)

from common import (  # noqa: E402
    CLASS_MAP,
    DATASETS,
    IMG_SIZE,
    MEAN,
    RAW,
    RESIZE,
    ROOT,
    SEED,
    STD,
    eval_transform,
    image_path,
    out_dir,
    sha256,
    source_of,
)
from train import build_model  # noqa: E402

TARGET_MACRO_F1 = 0.80
CATEGORY_TARGET = 0.90
UMB_DIR = ROOT / "data" / "umb"
CONFIDENT = 0.65  # umbral de confianza media de la API (SAD §7.5)


def numpy_preprocess(image: Image.Image) -> np.ndarray:
    """Igual que `eval_transform` (Resize 256 → CenterCrop 224 → normalizar), pero sin PyTorch."""
    image = image.convert("RGB")
    width, height = image.size
    short, long_ = (width, height) if width <= height else (height, width)
    new_long = int(RESIZE * long_ / short)
    size = (RESIZE, new_long) if width <= height else (new_long, RESIZE)
    image = image.resize(size, Image.BILINEAR)
    left = int(round((size[0] - IMG_SIZE) / 2.0))
    top = int(round((size[1] - IMG_SIZE) / 2.0))
    image = image.crop((left, top, left + IMG_SIZE, top + IMG_SIZE))
    array = np.asarray(image, dtype=np.float32) / 255.0
    array = (array - np.array(MEAN, dtype=np.float32)) / np.array(STD, dtype=np.float32)
    return array.transpose(2, 0, 1)


def softmax(logits: np.ndarray) -> np.ndarray:
    exp = np.exp(logits - logits.max(axis=1, keepdims=True))
    return exp / exp.sum(axis=1, keepdims=True)


def make_views(image: Image.Image, views: tuple[str, ...]) -> np.ndarray:
    """Igual que `preprocess_views` de la API: center, flip (espejo del recorte) y full (foto completa)."""
    center = numpy_preprocess(image)
    out = []
    for view in views:
        if view == "flip":
            out.append(np.ascontiguousarray(center[:, :, ::-1]))
        elif view == "full":
            squashed = image.convert("RGB").resize((IMG_SIZE, IMG_SIZE), Image.BILINEAR)
            array = np.asarray(squashed, dtype=np.float32) / 255.0
            out.append(((array - np.array(MEAN, dtype=np.float32)) / np.array(STD, dtype=np.float32)).transpose(2, 0, 1))
        else:
            out.append(center)
    return np.stack(out).astype(np.float32)


def read_views(destination: Path) -> tuple[str, ...]:
    config = destination / "inference.json"
    return tuple(json.loads(config.read_text(encoding="utf-8"))["views"]) if config.is_file() else ("center",)


def export_onnx(model: torch.nn.Module, destination: Path) -> None:
    dummy = torch.zeros(1, 3, IMG_SIZE, IMG_SIZE)
    torch.onnx.export(
        model, dummy, str(destination / "model.onnx"), input_names=["image"], output_names=["logits"],
        dynamic_axes={"image": {0: "batch"}, "logits": {0: "batch"}}, opset_version=17, dynamo=False,
    )
    onnx.checker.check_model(onnx.load(str(destination / "model.onnx")))


def run_probabilities(
    session: ort.InferenceSession, images: list[Image.Image], views: tuple[str, ...] = ("center",)
) -> np.ndarray:
    out = []
    for image in images:
        logits = session.run(None, {"image": make_views(image, views)})[0]
        out.append(softmax(logits).mean(axis=0))  # promedio de las vistas
    return np.array(out)


def load_images(paths: list[Path]) -> list[Image.Image]:
    images = []
    for path in paths:
        with Image.open(path) as image:
            images.append(image.convert("RGB"))
    return images


def check_parity(model: torch.nn.Module, session: ort.InferenceSession, paths: list[Path]) -> float:
    """Diferencia máxima entre PyTorch (torchvision) y ONNX (NumPy) sobre 30 imágenes de test."""
    worst = 0.0
    transform = eval_transform()
    for path in paths[:30]:
        with Image.open(path) as image:
            rgb = image.convert("RGB")
            expected = model(transform(rgb).unsqueeze(0)).detach().numpy()
            got = session.run(None, {"image": numpy_preprocess(rgb)[None]})[0]
        worst = max(worst, float(np.abs(expected - got).max()))
    return worst


def latency_ms(session: ort.InferenceSession) -> dict[str, float]:
    sample = np.random.default_rng(SEED).standard_normal((1, 3, IMG_SIZE, IMG_SIZE)).astype(np.float32)
    for _ in range(10):
        session.run(None, {"image": sample})
    times = []
    for _ in range(100):
        started = time.perf_counter()
        session.run(None, {"image": sample})
        times.append((time.perf_counter() - started) * 1000)
    times.sort()
    return {"median": round(statistics.median(times), 2), "p95": round(times[94], 2)}


def save_confusion(matrix: np.ndarray, classes: list[str], destination: Path) -> None:
    np.savetxt(destination / "confusion_matrix.csv", matrix, fmt="%d", delimiter=",", header=",".join(classes), comments="")
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.imshow(matrix, cmap="Greens")
    ax.set_xticks(range(len(classes)), classes, rotation=45, ha="right")
    ax.set_yticks(range(len(classes)), classes)
    ax.set_xlabel("Predicho")
    ax.set_ylabel("Real")
    for i in range(len(classes)):
        for j in range(len(classes)):
            ax.text(j, i, matrix[i, j], ha="center", va="center", color="black" if matrix[i, j] < matrix.max() / 2 else "white")
    ax.set_title("Matriz de confusión — test")
    fig.tight_layout()
    fig.savefig(destination / "confusion_matrix.png", dpi=150)


def umb_photos(classes: list[str]) -> list[tuple[Path, str]]:
    """Fotos reales de la UMB (carpeta = código del objeto del catálogo) que el modelo sabe reconocer."""
    if not UMB_DIR.is_dir():
        return []
    by_item = {CLASS_MAP[c]["item_code"]: c for c in classes}
    out = []
    for folder in sorted(p for p in UMB_DIR.iterdir() if p.is_dir() and p.name in by_item):
        for path in sorted(folder.iterdir()):
            if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
                out.append((path, by_item[folder.name]))
    return out


def subset_metrics(truth: np.ndarray, guess: np.ndarray, mask: np.ndarray) -> dict[str, float | int]:
    return {
        "n": int(mask.sum()),
        "macro_f1": round(float(f1_score(truth[mask], guess[mask], average="macro")), 4),
        "accuracy_top1": round(float(accuracy_score(truth[mask], guess[mask])), 4),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", default="v1")
    parser.add_argument("--dataset", default="trashnet", choices=list(DATASETS))
    args = parser.parse_args()
    spec = DATASETS[args.dataset]
    classes = spec.classes
    destination = out_dir(args.version)

    test = json.loads(spec.splits_file.read_text(encoding="utf-8"))["test"]
    splits = json.loads(spec.splits_file.read_text(encoding="utf-8"))
    paths = [image_path(rel) for rel, _ in test]
    config_file = destination / "config.json"
    arch = json.loads(config_file.read_text(encoding="utf-8"))["arch"] if config_file.is_file() else "mobilenet_v3_small"
    model = build_model(len(classes), arch)
    model.load_state_dict(torch.load(destination / "weights.pt", map_location="cpu"))
    model.eval()
    export_onnx(model, destination)
    session = ort.InferenceSession(str(destination / "model.onnx"), providers=["CPUExecutionProvider"])
    parity = check_parity(model, session, paths)

    truth = np.array([label for _, label in test])
    views = read_views(destination)
    proba = run_probabilities(session, load_images(paths), views)
    guess = proba.argmax(axis=1)
    sources = np.array([source_of(rel) for rel, _ in test])

    macro_f1 = float(f1_score(truth, guess, average="macro"))
    report = classification_report(truth, guess, labels=list(range(len(classes))), target_names=classes, output_dict=True, zero_division=0)
    top3 = float(np.mean([t in np.argsort(p)[-3:] for t, p in zip(truth, proba, strict=True)]))
    auc = {c: round(float(roc_auc_score(truth == i, proba[:, i])), 4) for i, c in enumerate(classes)}
    to_category = [CLASS_MAP[c]["category"] for c in classes]
    category_f1 = float(f1_score([to_category[t] for t in truth], [to_category[g] for g in guess], average="macro"))
    confident = proba.max(axis=1) >= CONFIDENT
    matrix = confusion_matrix(truth, guess, labels=list(range(len(classes))))
    save_confusion(matrix, classes, destination)

    field = umb_photos(classes)
    field_report: dict[str, object] | None = None
    if field:
        field_proba = run_probabilities(session, load_images([p for p, _ in field]), views)
        rows = []
        for (path, label), p in zip(field, field_proba, strict=True):
            top = int(p.argmax())
            rows.append({"file": f"{path.parent.name}/{path.name}", "expected": label, "predicted": classes[top],
                         "confidence": round(float(p[top]), 3), "correct": classes[top] == label,
                         "probability_of_expected": round(float(p[classes.index(label)]), 3)})
        field_report = {
            "n": len(rows), "accuracy_top1": round(sum(r["correct"] for r in rows) / len(rows), 3),  # type: ignore[misc]
            "note": "fotos reales de la UMB etiquetadas a mano o por usuarios; muestra muy pequeña: es anecdótica",
            "photos": rows,
        }

    metrics = {
        "model": f"{arch} (ImageNet) + cabeza de {len(classes)} clases",
        "arch": arch,
        "classes": classes,
        "inference_views": list(views),
        "dataset": {
            "name": spec.name,
            "sources": list(spec.sources),
            "zip_sha256": {"trashnet": sha256(RAW / "dataset-resized.zip"), **({"realwaste": sha256(RAW / "realwaste.zip")} if "realwaste" in spec.sources else {})},
            "split": {k: len(v) for k, v in splits.items()},
            "seed": SEED,
        },
        "test": {
            "macro_f1": round(macro_f1, 4), "accuracy_top1": round(float(accuracy_score(truth, guess)), 4),
            "accuracy_top3": round(top3, 4), "category_macro_f1": round(category_f1, 4),
            "per_class": {c: {k: round(report[c][k], 4) for k in ("precision", "recall", "f1-score", "support")} for c in classes},
            "roc_auc_ovr": auc,
            "per_source": {s: subset_metrics(truth, guess, sources == s) for s in spec.sources},
            f"share_with_confidence_ge_{CONFIDENT}": round(float(confident.mean()), 4),
            f"accuracy_when_confidence_ge_{CONFIDENT}": round(float(np.mean(truth[confident] == guess[confident])), 4),
        },
        "umb_photos": field_report,
        "targets": {"macro_f1": TARGET_MACRO_F1, "macro_f1_met": macro_f1 >= TARGET_MACRO_F1,
                    "category_macro_f1": CATEGORY_TARGET, "category_macro_f1_met": category_f1 >= CATEGORY_TARGET},
        "deployment": {"onnx_size_mb": round((destination / "model.onnx").stat().st_size / 1e6, 2),
                       "latency_ms_cpu_1_image": latency_ms(session),
                       "max_abs_logit_diff_torch_vs_onnx": round(parity, 6)},
        "environment": {"python": platform.python_version(), "torch": torch.__version__, "torchvision": torchvision.__version__,
                        "onnx": onnx.__version__, "onnxruntime": ort.__version__, "scikit-learn": sklearn.__version__},
    }
    (destination / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    (destination / "labels.json").write_text(json.dumps(classes), encoding="utf-8")
    (destination / "class_map.json").write_text(json.dumps({c: CLASS_MAP[c] for c in classes}, indent=2), encoding="utf-8")
    (destination / "splits.json").write_text(spec.splits_file.read_text(encoding="utf-8"), encoding="utf-8")
    print(json.dumps({k: v for k, v in metrics["test"].items() if k != "roc_auc_ovr"}, indent=2, ensure_ascii=False))
    print(json.dumps({"umb_photos": field_report, "targets": metrics["targets"], "deployment": metrics["deployment"]}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
