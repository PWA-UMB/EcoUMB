"""Elige con VALIDACIÓN qué vistas de la foto conviene promediar al clasificar (y lo guarda para la API).

Uso (desde ml/, después de evaluate.py):  .venv/Scripts/python src/select_views.py --version v2 --dataset combined

Compara «solo el recorte central» contra promediar también la vista espejada y la foto completa. Se elige
por Macro F1 de validación (nunca por test) y solo si mejora al menos 0,005; si no, se deja el recorte
central. Escribe ``inference.json``, que la API lee al arrancar. Los resultados de test de cada opción se
guardan solo para transparencia.
"""

import argparse
import json

import numpy as np
import onnxruntime as ort
from sklearn.metrics import f1_score

from common import DATASETS, image_path, out_dir
from evaluate import load_images, run_probabilities

CANDIDATES = {
    "center": ("center",),
    "center+flip": ("center", "flip"),
    "center+flip+full": ("center", "flip", "full"),
}
MIN_GAIN = 0.005


def score(session: ort.InferenceSession, items: list, views: tuple[str, ...]) -> tuple[float, float]:
    images = load_images([image_path(rel) for rel, _ in items])
    truth = np.array([label for _, label in items])
    guess = run_probabilities(session, images, views).argmax(axis=1)
    return float(f1_score(truth, guess, average="macro")), float((truth == guess).mean())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", required=True)
    parser.add_argument("--dataset", default="trashnet", choices=list(DATASETS))
    args = parser.parse_args()
    destination = out_dir(args.version)
    splits = json.loads(DATASETS[args.dataset].splits_file.read_text(encoding="utf-8"))
    session = ort.InferenceSession(str(destination / "model.onnx"), providers=["CPUExecutionProvider"])

    report = {}
    for name, views in CANDIDATES.items():
        val_f1, _ = score(session, splits["val"], views)
        test_f1, test_acc = score(session, splits["test"], views)
        report[name] = {"val_macro_f1": round(val_f1, 4), "test_macro_f1": round(test_f1, 4), "test_accuracy": round(test_acc, 4)}
        print(f"{name:<18} val F1={val_f1:.4f}   test F1={test_f1:.4f}  acc={test_acc:.4f}", flush=True)

    baseline = report["center"]["val_macro_f1"]
    best = max(report, key=lambda name: report[name]["val_macro_f1"])
    chosen = best if report[best]["val_macro_f1"] >= baseline + MIN_GAIN else "center"
    (destination / "inference.json").write_text(json.dumps({"views": list(CANDIDATES[chosen])}), encoding="utf-8")
    (destination / "views_selection.json").write_text(
        json.dumps({"chosen": chosen, "criterion": f"Macro F1 de validación (mejora mínima {MIN_GAIN})", "options": report}, indent=2),
        encoding="utf-8",
    )
    print("Elegida:", chosen)


if __name__ == "__main__":
    main()
