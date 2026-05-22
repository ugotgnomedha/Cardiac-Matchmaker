import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.models.base.base_model import db
from app.models.dataset.dataset_model import Dataset
from app.services.project.project_service import ProjectService


class DatasetServiceError(Exception):
    def __init__(self, detail: Any):
        super().__init__(str(detail))
        self.detail = detail


class DatasetCreatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=255)
    type: str = Field(min_length=1, max_length=50)
    original_filename: str = Field(min_length=1, max_length=255)
    storage_path: str = Field(min_length=1)
    metadata: dict[str, Any] | None = None


class DatasetRead(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    type: str
    original_filename: str
    storage_path: str
    metadata: dict[str, Any] | None
    created_at: datetime.datetime
    updated_at: datetime.datetime


class DatasetService:
    def __init__(self) -> None:
        self.project_service = ProjectService()

    def create_dataset(self, project_id: UUID, payload: DatasetCreatePayload) -> DatasetRead:
        project = self.project_service.get_project_model(project_id)

        with db.atomic():
            dataset = Dataset.create(
                id=uuid4(),
                project=project,
                name=payload.name,
                type=payload.type,
                original_filename=payload.original_filename,
                storage_path=payload.storage_path,
                metadata=payload.metadata,
            )

        return self._to_read_model(dataset)

    def list_datasets(self, project_id: UUID) -> list[DatasetRead]:
        self.project_service.get_project_model(project_id)
        datasets = (
            Dataset.select()
            .where(Dataset.project == project_id)
            .order_by(Dataset.created_at.desc())
        )
        return [self._to_read_model(dataset) for dataset in datasets]

    def _to_read_model(self, dataset: Dataset) -> DatasetRead:
        return DatasetRead(
            id=getattr(dataset, "id"),
            project_id=getattr(dataset, "project_id"),
            name=getattr(dataset, "name"),
            type=getattr(dataset, "type"),
            original_filename=getattr(dataset, "original_filename"),
            storage_path=getattr(dataset, "storage_path"),
            metadata=getattr(dataset, "metadata"),
            created_at=getattr(dataset, "created_at"),
            updated_at=getattr(dataset, "updated_at"),
        )
