import csv
import datetime
import os
from pathlib import Path
from typing import Any, Iterator
from uuid import UUID, uuid4

from app.models.base.base_model import db
from app.models.dataset.dataset_model import DatasetVersion
from app.models.feature.feature_model import FeatureAnnotation
from app.models.preprocessing.preprocessing_run_model import PreprocessingRun
from app.models.sample.sample_model import Sample, Measurement


def _clean(value: Any) -> str | None:
    """Normalise a TSV cell: blanks and explicit NA become None."""
    if value is None:
        return None
    text = str(value).strip()
    return None if text in ("", "NA") else text


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

    # "largeAtery" (sic) is the spelling used in the source proteomics file;
    # "largeArtery" is kept so earlier fixtures keep classifying correctly.
    HEART_SAMPLE_PATTERNS = ["largeArtery", "largeAtery", "coronaryArtery", "Atrium", "Ventricle", "AV-Valves", "SL-Valves"]

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
            annotations: dict[str, dict[str, Any]] = {}  # GeneName -> annotation fields
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

                    self._collect_annotation(annotations, gene_name, row)

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

                self._store_annotations(dataset_version_id, annotations)

            # update the DatasetVersion status
            dataset_version = DatasetVersion.get_by_id(dataset_version_id)
            dataset_version.status = "normalized"  # pyrefly: ignore
            dataset_version.save()

    def _collect_annotation(self, annotations: dict[str, dict[str, Any]], gene_name: str, row: dict[str, Any]) -> None:
        """Accumulate one feature's annotation from a TSV row.

        The same gene can appear on several rows; descriptive fields take the
        first non-empty value and ``present_in_heart`` is true if any row flags it.
        """
        present = (str(row.get("match_in_heart", "")).strip().upper() == "TRUE")
        existing = annotations.get(gene_name)
        if existing is None:
            annotations[gene_name] = {
                "uniprot": _clean(row.get("UniProt")),
                "matrisome_division": _clean(row.get("MatrisomeDivision")),
                "matrisome_category": _clean(row.get("MatrisomeCategory")),
                "location": _clean(row.get("Location")),
                "present_in_heart": present,
            }
            return
        existing["present_in_heart"] = existing["present_in_heart"] or present
        for field, column in (
            ("uniprot", "UniProt"),
            ("matrisome_division", "MatrisomeDivision"),
            ("matrisome_category", "MatrisomeCategory"),
            ("location", "Location"),
        ):
            if existing[field] is None:
                existing[field] = _clean(row.get(column))

    def _store_annotations(self, dataset_version_id: UUID, annotations: dict[str, dict[str, Any]]) -> None:
        """Persist the collected per-feature annotations."""
        for gene_name, fields in annotations.items():
            FeatureAnnotation.create(
                id=uuid4(),
                dataset_version=dataset_version_id,
                feature_name=gene_name,
                **fields,
            )