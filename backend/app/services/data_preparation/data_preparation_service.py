import csv
import datetime
import os
from pathlib import Path
from typing import Any, Iterator
from uuid import UUID, uuid4

from app.models.base.base_model import db
from app.models.dataset.dataset_model import DatasetVersion
from app.models.preprocessing.preprocessing_run_model import PreprocessingRun
from app.models.sample.sample_model import Sample, Measurement


class DataPreparationError(Exception):
    def __init__(self, detail: Any):
        super().__init__(str(detail))
        self.detail = detail


class DataPreparationService:
    """Parse placenta+heart TSV and populate Sample/Measurement tables."""

    METADATA_COLUMNS = {
        "GeneName", "UniProt", "Location", "MatrisomeDivision",
        "MatrisomeCategory", "match_in_heart"
    }

    HEART_SAMPLE_PATTERNS = ["largeArtery", "coronaryArtery", "Atrium", "Ventricle", "AV-Valves", "SL-Valves"]

    def ingest_dataset_version(
        self,
        dataset_version_id: UUID,
        file_path: Path,
        log_path: Path | None = None,
    ) -> PreprocessingRun:
        """Parse TSV file and populate samples/measurements for the given dataset version."""
        run = PreprocessingRun.create(
            id=uuid4(),
            dataset_version=dataset_version_id,
            status="running",
            config={"parser": "placenta_heart_tsv", "file": str(file_path)},
            log_path=str(log_path) if log_path else None,
            started_at=datetime.datetime.now(datetime.timezone.utc),
        )

        try:
            self._parse_and_store(dataset_version_id, file_path, run)
            run.status = "completed"  # pyrefly: ignore
            run.finished_at = datetime.datetime.now(datetime.timezone.utc)  # pyrefly: ignore
            run.save()
        except Exception as e:
            run.status = "failed"  # pyrefly: ignore
            run.error_message = str(e)  # pyrefly: ignore
            run.finished_at = datetime.datetime.now(datetime.timezone.utc)  # pyrefly: ignore
            run.save()
            raise DataPreparationError(f"Ingestion failed: {e}") from e

        return run

    def _parse_and_store(self, dataset_version_id: UUID, file_path: Path, run: PreprocessingRun) -> None:
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            if not reader.fieldnames:
                raise ValueError("TSV has no header")

            sample_columns = [col for col in reader.fieldnames if col not in self.METADATA_COLUMNS]

            sample_map = {}  # column_name -> Sample instance
            with db.atomic():
                for col in sample_columns:
                    sample_type = "heart_region" if any(pat in col for pat in self.HEART_SAMPLE_PATTERNS) else "placenta_region"
                    sample = Sample.create(
                        id=uuid4(),
                        dataset_version=dataset_version_id,
                        name=col,
                        type=sample_type,
                        metadata={"source_file": str(file_path)},
                    )
                    sample_map[col] = sample

                for row_num, row in enumerate(reader, start=2):  # row 1 is header
                    gene_name = row.get("GeneName", "").strip()
                    if not gene_name:
                        continue  # skip rows without gene name

                    for col, value in row.items():
                        if col not in sample_map:
                            continue  # skip metadata columns
                        if value in (None, "", "NA"):
                            continue
                        try:
                            raw_val = float(value)
                        except (ValueError, TypeError):
                            continue  # skip non‑numeric values

                        Measurement.create(
                            id=uuid4(),
                            sample=sample_map[col],
                            feature_name=gene_name,
                            raw_value=raw_val,
                            normalized_value=None,
                            unit="log2 intensity",
                        )

            # update the DatasetVersion status
            dataset_version = DatasetVersion.get_by_id(dataset_version_id)
            dataset_version.status = "normalized"  # pyrefly: ignore
            dataset_version.save()