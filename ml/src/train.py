"""Entrena el modelo: MobileNetV3-Small con transfer learning (SAD §7.2).

Uso (desde ml/):
  .venv/Scripts/python src/train.py                                       # v1: TrashNet, 6 clases
  .venv/Scripts/python src/train.py --version v2 --dataset combined --robust   # v2: + RealWaste, 8 clases

Fase 1 entrena solo la cabeza clasificadora; la fase 2 ajusta además los últimos bloques del extractor.
Se conserva el estado con mejor Macro F1 de validación. El conjunto de test NO se usa para elegir nada:
solo se evalúa una vez, en evaluate.py.
"""

import argparse
import csv
import json
import time

import torch
from sklearn.metrics import f1_score
from torch import nn
from torch.utils.data import DataLoader
from torchvision import models

from common import (
    DATASETS,
    SEED,
    ImageDataset,
    eval_transform,
    load_donors,
    make_splits,
    out_dir,
    seed_everything,
    train_transforms_by_source,
)

HEAD_EPOCHS, FINE_TUNE_EPOCHS = 5, 12  # valores de v1; --head-epochs / --fine-tune-epochs los cambian
HEAD_LR, FINE_TUNE_LR = 1e-3, 2e-4
BATCH_SIZE = 32
UNFREEZE_FROM = 8  # bloques de `features` que se descongelan en la fase 2 (de 13)
LABEL_SMOOTHING = 0.05


ARCHITECTURES = ("mobilenet_v3_small", "mobilenet_v3_large", "efficientnet_b0")


def build_model(num_classes: int, arch: str = "mobilenet_v3_small") -> nn.Module:
    """Modelo preentrenado en ImageNet con la cabeza cambiada por una de `num_classes` clases."""
    if arch == "mobilenet_v3_small":
        model = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.IMAGENET1K_V1)
        model.classifier[3] = nn.Linear(model.classifier[3].in_features, num_classes)
    elif arch == "mobilenet_v3_large":
        model = models.mobilenet_v3_large(weights=models.MobileNet_V3_Large_Weights.IMAGENET1K_V2)
        model.classifier[3] = nn.Linear(model.classifier[3].in_features, num_classes)
    elif arch == "efficientnet_b0":
        model = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.IMAGENET1K_V1)
        model.classifier[1] = nn.Linear(model.classifier[1].in_features, num_classes)
    else:
        raise ValueError(f"arquitectura desconocida: {arch}")
    return model


def set_trainable(model: nn.Module, unfreeze_from: int | None) -> list[nn.Parameter]:
    """`None` = solo la cabeza; un índice = cabeza + bloques de `features` desde ese índice."""
    for parameter in model.parameters():
        parameter.requires_grad = False
    for parameter in model.classifier.parameters():
        parameter.requires_grad = True
    if unfreeze_from is not None:
        for block in model.features[unfreeze_from:]:
            for parameter in block.parameters():
                parameter.requires_grad = True
    return [p for p in model.parameters() if p.requires_grad]


def class_weights(train_items: list[tuple[str, int]], num_classes: int) -> torch.Tensor:
    counts = torch.zeros(num_classes)
    for _, label in train_items:
        counts[label] += 1
    return counts.sum() / (num_classes * counts)  # inverso a la frecuencia de cada clase


@torch.no_grad()
def predict(model: nn.Module, loader: DataLoader, device: str = "cpu") -> tuple[list[int], list[int]]:
    model.eval()
    truth: list[int] = []
    guess: list[int] = []
    for images, labels in loader:
        guess.extend(model(images.to(device)).argmax(dim=1).tolist())
        truth.extend(labels.tolist())
    return truth, guess


def run_epoch(
    model: nn.Module, loader: DataLoader, loss_fn: nn.Module, optimizer: torch.optim.Optimizer, device: str = "cpu"
) -> float:
    model.train()
    total = 0.0
    for images, labels in loader:
        optimizer.zero_grad()
        loss = loss_fn(model(images.to(device)), labels.to(device))
        loss.backward()
        optimizer.step()
        total += loss.item() * len(labels)
    return total / len(loader.dataset)  # type: ignore[arg-type]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", default="v1", help="carpeta de salida en models/")
    parser.add_argument("--dataset", default="trashnet", choices=list(DATASETS))
    parser.add_argument("--robust", action="store_true", help="aumentos de campo (fondos, oclusiones, matiz)")
    parser.add_argument("--arch", default="mobilenet_v3_small", choices=ARCHITECTURES)
    parser.add_argument("--head-epochs", type=int, default=HEAD_EPOCHS)
    parser.add_argument("--unfreeze-from", type=int, default=UNFREEZE_FROM, help="0 = ajustar todo el extractor")
    parser.add_argument("--fine-tune-lr", type=float, default=FINE_TUNE_LR)
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--fine-tune-epochs", type=int, default=FINE_TUNE_EPOCHS)
    args = parser.parse_args()

    seed_everything()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print("dispositivo:", device, "| arquitectura:", args.arch, flush=True)
    spec = DATASETS[args.dataset]
    destination = out_dir(args.version)
    destination.mkdir(parents=True, exist_ok=True)
    splits = make_splits(spec)
    print({name: len(items) for name, items in splits.items()}, spec.name, "robusto" if args.robust else "clasico", flush=True)
    donors = load_donors([i for i in splits["train"] if not i[0].startswith("realwaste/")]) if args.robust else None

    generator = torch.Generator().manual_seed(SEED)
    train_loader = DataLoader(
        ImageDataset(splits["train"], train_transforms_by_source(args.robust, donors)),
        batch_size=args.batch_size, shuffle=True, num_workers=args.workers, persistent_workers=True,
        pin_memory=device == "cuda", generator=generator,
    )
    val_loader = DataLoader(
        ImageDataset(splits["val"], eval_transform()), batch_size=64, num_workers=2, pin_memory=device == "cuda"
    )

    model = build_model(len(spec.classes), args.arch).to(device)
    (destination / "config.json").write_text(
        json.dumps({"arch": args.arch, "dataset": args.dataset, "robust": args.robust, "args": vars(args)}, indent=2, default=str),
        encoding="utf-8",
    )
    loss_fn = nn.CrossEntropyLoss(
        weight=class_weights(splits["train"], len(spec.classes)).to(device), label_smoothing=LABEL_SMOOTHING
    )
    best_f1, best_state = -1.0, None
    log_rows: list[dict[str, float | int | str]] = []

    phases = [
        ("cabeza", None, args.head_epochs, HEAD_LR),
        ("ajuste fino", args.unfreeze_from, args.fine_tune_epochs, args.fine_tune_lr),
    ]
    epoch = 0
    for phase, unfreeze_from, epochs, lr in phases:
        optimizer = torch.optim.AdamW(set_trainable(model, unfreeze_from), lr=lr, weight_decay=1e-4)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
        for _ in range(epochs):
            epoch += 1
            started = time.time()
            loss = run_epoch(model, train_loader, loss_fn, optimizer, device)
            scheduler.step()
            truth, guess = predict(model, val_loader, device)
            val_f1 = f1_score(truth, guess, average="macro")
            val_acc = sum(t == g for t, g in zip(truth, guess, strict=True)) / len(truth)
            log_rows.append({"epoch": epoch, "phase": phase, "train_loss": round(loss, 4),
                             "val_macro_f1": round(val_f1, 4), "val_accuracy": round(val_acc, 4)})
            print(f"[{epoch:02d}] {phase:<11} loss={loss:.4f} val_macroF1={val_f1:.4f} val_acc={val_acc:.4f} ({time.time() - started:.0f}s)", flush=True)
            if val_f1 > best_f1:
                best_f1 = val_f1
                best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}

    assert best_state is not None
    torch.save(best_state, destination / "weights.pt")
    with (destination / "train_log.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(log_rows[0]))
        writer.writeheader()
        writer.writerows(log_rows)
    print(f"Mejor Macro F1 de validación: {best_f1:.4f}. Pesos guardados en {destination / 'weights.pt'}")


if __name__ == "__main__":
    main()
