from uuid import uuid4

import pytest

from app.models.dataset.dataset_model import Dataset
from app.services.dataset.dataset_service import DatasetCreatePayload, DatasetService
from app.services.project.project_service import ProjectNotFoundError


def make_dataset_payload(
    *,
    name: str = "Placenta proteomics",
    storage_path: str = "/data/raw/placenta.tsv",
) -> DatasetCreatePayload:
    return DatasetCreatePayload(
        name=name,
        type="placenta",
        original_filename=storage_path.rsplit("/", maxsplit=1)[-1],
        storage_path=storage_path,
        metadata={"delimiter": "tab", "source": "service-test"},
    )


def test_dataset_service_creates_dataset_with_project_scope(service_context):
    project = service_context.create_project_model()
    other_project = service_context.create_project_model()
    service = DatasetService()

    first_dataset = service.create_dataset(
        project.id,
        make_dataset_payload(name="Placenta raw", storage_path="/data/raw/placenta.tsv"),
    )
    second_dataset = service.create_dataset(
        project.id,
        make_dataset_payload(name="Placenta normalized", storage_path="/data/processed/placenta.tsv"),
    )
    service.create_dataset(
        other_project.id,
        make_dataset_payload(name="Other project dataset", storage_path="/data/raw/other.tsv"),
    )

    project_datasets = service.list_datasets(project.id)
    project_dataset_ids = {dataset.id for dataset in project_datasets}

    assert project_dataset_ids == {first_dataset.id, second_dataset.id}
    assert all(dataset.project_id == project.id for dataset in project_datasets)
    assert first_dataset.metadata == {"delimiter": "tab", "source": "service-test"}


def test_dataset_service_persists_dataset_row(service_context):
    project = service_context.create_project_model()

    created_dataset = DatasetService().create_dataset(
        project.id,
        make_dataset_payload(name="Cardiac reference", storage_path="/data/raw/cardiac.tsv"),
    )

    persisted_dataset = Dataset.get_by_id(created_dataset.id)
    assert persisted_dataset.project.id == project.id
    assert persisted_dataset.name == "Cardiac reference"
    assert persisted_dataset.storage_path == "/data/raw/cardiac.tsv"


def test_dataset_service_raises_for_missing_project(migrated_db):
    missing_project_id = uuid4()

    with pytest.raises(ProjectNotFoundError, match=str(missing_project_id)):
        DatasetService().list_datasets(missing_project_id)
