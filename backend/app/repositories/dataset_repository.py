from typing import Any
from uuid import UUID, uuid4

from app.models.base.base_model import db
from app.models.dataset.dataset_model import Dataset
from app.models.project.project_model import ResearchProject


class DatasetRepository:
    def create(
        self,
        *,
        project: ResearchProject,
        name: str,
        type: str,
        original_filename: str,
        storage_path: str,
        metadata: dict[str, Any] | None = None,
    ) -> Dataset:
        with db.atomic():
            return Dataset.create(
                id=uuid4(),
                project=project,
                name=name,
                type=type,
                original_filename=original_filename,
                storage_path=storage_path,
                metadata=metadata,
            )

    def list_for_project(self, project_id: UUID) -> list[Dataset]:
        return list(
            Dataset.select()
            .where(Dataset.project == project_id)
            .order_by(Dataset.created_at.desc())
        )

    def get(self, dataset_id: UUID) -> Dataset | None:
        return Dataset.get_or_none(Dataset.id == dataset_id)

    def update(self, dataset: Dataset, values: dict[str, Any]) -> Dataset:
        for field_name, value in values.items():
            setattr(dataset, field_name, value)

        with db.atomic():
            dataset.save()
        return dataset

    def delete(self, dataset: Dataset) -> int:
        with db.atomic():
            return dataset.delete_instance(recursive=True)
