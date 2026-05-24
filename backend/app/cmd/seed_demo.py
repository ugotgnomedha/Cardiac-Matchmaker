import argparse
from collections.abc import Sequence
from pathlib import Path
from typing import Any, TypedDict

from app.cmd.migrate import ensure_migrations_applied
from app.models.base.base_model import db
from app.models.dataset.dataset_model import Dataset, DatasetVersion
from app.models.project.project_model import ResearchProject


DEFAULT_STORAGE_DIRS = ("raw", "processed", "pdfs", "logs", "reports")


class SeedResult(TypedDict):
    storage_paths: dict[str, Path]
    project: ResearchProject
    project_created: bool
    dataset: Dataset
    dataset_created: bool
    dataset_version: DatasetVersion
    version_created: bool


def get_repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def create_storage_layout(storage_root: Path) -> dict[str, Path]:
    paths = {}
    for directory_name in DEFAULT_STORAGE_DIRS:
        path = storage_root / directory_name
        path.mkdir(parents=True, exist_ok=True)
        paths[directory_name] = path
    return paths


def get_first_or_create(model, defaults: dict[str, Any] | None = None, **query):
    expressions = [getattr(model, field_name) == value for field_name, value in query.items()]
    instance = model.select().where(*expressions).first()
    if instance is not None:
        return instance, False

    values = dict(query)
    if defaults:
        values.update(defaults)
    return model.create(**values), True


def seed_demo_project(storage_root: Path) -> SeedResult:
    storage_paths = create_storage_layout(storage_root)

    project, project_created = get_first_or_create(
        ResearchProject,
        name="Demo Cardiac Matchmaker Project",
        defaults={
            "description": (
                "Demo project for placenta-to-cardiac tissue matching with raw uploads, "
                "processed artifacts, literature PDFs, logs, and reports."
            )
        },
    )

    dataset, dataset_created = get_first_or_create(
        Dataset,
        project=project,
        name="Demo placenta proteomics dataset",
        defaults={
            "type": "placenta",
            "original_filename": "demo_placenta_proteomics.tsv",
            "storage_path": str(storage_paths["raw"] / "demo_placenta_proteomics.tsv"),
            "metadata": {
                "source": "demo",
                "tissue_regions": ["amnion", "chorion", "basal tissue", "umbilical cord"],
                "purpose": "seed data for development",
            },
        },
    )

    dataset_version, version_created = get_first_or_create(
        DatasetVersion,
        dataset=dataset,
        version_number="1",
        defaults={
            "status": "raw",
            "storage_path": dataset.storage_path,
            "preprocessing_config": {"normalization": "pending"},
        },
    )

    return {
        "storage_paths": storage_paths,
        "project": project,
        "project_created": project_created,
        "dataset": dataset,
        "dataset_created": dataset_created,
        "dataset_version": dataset_version,
        "version_created": version_created,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Seed demo Cardiac Matchmaker project data")
    parser.add_argument(
        "--storage-root",
        default=str(get_repo_root() / "data"),
        help="Root directory for raw, processed, pdfs, logs, and reports folders.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    storage_root = Path(args.storage_root).resolve()

    try:
        db.connect(reuse_if_open=True)
        ensure_migrations_applied()
        result = seed_demo_project(storage_root)
    finally:
        if not db.is_closed():
            db.close()

    print(f"Storage root: {storage_root}")
    for name, path in result["storage_paths"].items():
        print(f" - {name}: {path}")

    print(f"Project: {result['project'].name} ({result['project'].id})")
    print(f"Dataset: {result['dataset'].name} ({result['dataset'].id})")
    print(f"Dataset version: {result['dataset_version'].version_number} ({result['dataset_version'].id})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
