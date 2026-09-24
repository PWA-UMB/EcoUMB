"""Exporta las fotos que los usuarios etiquetaron (RF-29/30) como dataset para reentrenar (RF-31).

Genera ``<salida>/<objeto>/<id>.<ext>`` y un ``manifest.csv`` sin identificadores de usuario:
sirve para entrenar, no para rastrear a quien subió la foto (RNF-08, protección de datos).
"""

import csv
import shutil
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models import ClassificationModel, WasteItemModel
from app.infrastructure.storage.local import LocalImageStorage

MANIFEST = "manifest.csv"
FIELDS = ["id", "file", "label", "predicted", "was_corrected", "confidence", "created_at"]


@dataclass(frozen=True)
class ExportSummary:
    exported: int
    skipped_missing_file: int
    per_label: dict[str, int]


def export_feedback(
    session: Session, storage: LocalImageStorage, out_dir: Path, *, only_corrected: bool = False
) -> ExportSummary:
    """Copia cada foto con respuesta del usuario a la carpeta de su objeto real."""
    codes = {i.id: i.code for i in session.scalars(select(WasteItemModel))}
    query = select(ClassificationModel).where(ClassificationModel.final_item_id.is_not(None))
    if only_corrected:
        query = query.where(ClassificationModel.was_corrected.is_(True))

    out_dir.mkdir(parents=True, exist_ok=True)
    per_label: Counter[str] = Counter()
    skipped = 0
    rows: list[dict[str, str]] = []
    for record in session.scalars(query.order_by(ClassificationModel.created_at)):
        assert record.final_item_id is not None  # el filtro de arriba lo garantiza  # noqa: S101
        label = codes[record.final_item_id]
        try:
            source = storage.path_of(record.image_url)
        except ValueError:
            skipped += 1
            continue
        if not source.is_file():
            skipped += 1
            continue
        target = Path(label) / f"{record.id}{source.suffix}"
        (out_dir / label).mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, out_dir / target)
        per_label[label] += 1
        rows.append(
            {
                "id": str(record.id),
                "file": target.as_posix(),
                "label": label,
                "predicted": codes.get(record.ai_predicted_item_id or record.final_item_id, ""),
                "was_corrected": str(record.was_corrected).lower(),
                "confidence": str(record.confidence or ""),
                "created_at": record.created_at.isoformat(),
            }
        )
    with (out_dir / MANIFEST).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return ExportSummary(len(rows), skipped, dict(per_label))
