"""Exporta el dataset de fotos etiquetadas por los usuarios (para reentrenar el modelo).

Uso (dentro del contenedor de la API):
  docker compose exec api python -m scripts.export_feedback --out /tmp/umb_dataset
  docker compose cp api:/tmp/umb_dataset ml/data/umb
"""

import argparse
from pathlib import Path

from app.core.config import get_settings
from app.infrastructure.dataset_export import export_feedback
from app.infrastructure.persistence.session import create_db_engine, create_session_factory
from app.infrastructure.storage.local import LocalImageStorage


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--out", type=Path, required=True, help="carpeta de salida")
    parser.add_argument(
        "--only-corrected", action="store_true", help="solo las que el usuario corrigió"
    )
    args = parser.parse_args()

    settings = get_settings()
    session_factory = create_session_factory(create_db_engine(settings.database_url))
    with session_factory() as session:
        summary = export_feedback(
            session,
            LocalImageStorage(Path(settings.storage_dir)),
            args.out,
            only_corrected=args.only_corrected,
        )
    print(
        f"Exportadas {summary.exported} fotos a {args.out} "
        f"({summary.skipped_missing_file} sin archivo)"
    )
    for label, count in sorted(summary.per_label.items()):
        print(f"  {label:<26}{count}")


if __name__ == "__main__":
    main()
