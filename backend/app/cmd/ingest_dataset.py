import argparse
from pathlib import Path

from app.cmd.migrate import ensure_migrations_applied
from app.models.base.base_model import db
from app.models.dataset.dataset_model import DatasetVersion
from app.services.data_preparation.data_preparation_service import DataPreparationError, DataPreparationService


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest a dataset TSV file into samples and measurements")
    parser.add_argument("dataset_version_id", help="UUID of the DatasetVersion to associate")
    parser.add_argument("file_path", help="Path to the TSV file")
    parser.add_argument("--log-path", help="Optional path to store the log", default=None)
    args = parser.parse_args()

    try:
        db.connect(reuse_if_open=True)
        ensure_migrations_applied()

        version_id = args.dataset_version_id
        file_path = Path(args.file_path).resolve()
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        service = DataPreparationService()
        run = service.ingest_dataset_version(version_id, file_path, Path(args.log_path) if args.log_path else None)

        print(f"Ingestion completed. PreprocessingRun ID: {run.id} | Status: {run.status}")
        return 0
    except (DataPreparationError, FileNotFoundError, ValueError) as e:
        print(f"Error: {e}")
        return 1
    finally:
        if not db.is_closed():
            db.close()


if __name__ == "__main__":
    raise SystemExit(main())