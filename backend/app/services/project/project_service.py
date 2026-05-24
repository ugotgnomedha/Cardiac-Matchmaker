import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.models.base.base_model import db
from app.models.project.project_model import ResearchProject


class ProjectServiceError(Exception):
    def __init__(self, detail: Any):
        super().__init__(str(detail))
        self.detail = detail


class ProjectValidationError(ProjectServiceError):
    pass


class ProjectNotFoundError(ProjectServiceError):
    pass


class ProjectCreatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class ProjectUpdatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None


class ProjectRead(BaseModel):
    id: UUID
    name: str
    description: str | None
    created_at: datetime.datetime
    updated_at: datetime.datetime


class ProjectService:
    def create_project(self, payload: ProjectCreatePayload) -> ProjectRead:
        with db.atomic():
            project = ResearchProject.create(
                id=uuid4(),
                name=payload.name,
                description=payload.description,
            )

        return self._to_read_model(project)

    def list_projects(self) -> list[ProjectRead]:
        projects = ResearchProject.select().order_by(ResearchProject.created_at.desc())
        return [self._to_read_model(project) for project in projects]

    def get_project(self, project_id: UUID) -> ProjectRead:
        project = self.get_project_model(project_id)
        return self._to_read_model(project)

    def update_project(self, project_id: UUID, payload: ProjectUpdatePayload) -> ProjectRead:
        update_data = payload.model_dump(exclude_unset=True)
        if not update_data:
            raise ProjectValidationError("at least one field must be provided for update")

        project = self.get_project_model(project_id)
        for field_name, value in update_data.items():
            setattr(project, field_name, value)

        with db.atomic():
            project.save()

        return self._to_read_model(project)

    def get_project_model(self, project_id: UUID) -> ResearchProject:
        project = ResearchProject.get_or_none(ResearchProject.id == project_id)
        if project is None:
            raise ProjectNotFoundError(f"project {project_id} not found")
        return project

    def _to_read_model(self, project: ResearchProject) -> ProjectRead:
        return ProjectRead(
            id=getattr(project, "id"),
            name=getattr(project, "name"),
            description=getattr(project, "description"),
            created_at=getattr(project, "created_at"),
            updated_at=getattr(project, "updated_at"),
        )
