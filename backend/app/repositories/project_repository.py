from typing import Any
from uuid import UUID, uuid4

from app.models.base.base_model import db
from app.models.project.project_model import ResearchProject


class ProjectRepository:
    def create(self, *, name: str, description: str | None = None) -> ResearchProject:
        with db.atomic():
            return ResearchProject.create(id=uuid4(), name=name, description=description)

    def list(self) -> list[ResearchProject]:
        return list(ResearchProject.select().order_by(ResearchProject.created_at.desc()))

    def get(self, project_id: UUID) -> ResearchProject | None:
        return ResearchProject.get_or_none(ResearchProject.id == project_id)

    def update(self, project: ResearchProject, values: dict[str, Any]) -> ResearchProject:
        for field_name, value in values.items():
            setattr(project, field_name, value)

        with db.atomic():
            project.save()
        return project

    def delete(self, project: ResearchProject) -> int:
        with db.atomic():
            return project.delete_instance(recursive=True)
