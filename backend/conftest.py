from dataclasses import dataclass, field
from typing import cast
from uuid import UUID, uuid4

import pytest

from app.cmd.migrate import ensure_migrations_applied
from app.models.base.base_model import db
from app.models.job.job_model import ProcessingJob
from app.models.project.project_model import ResearchProject


@pytest.fixture()
def migrated_db():
    db.connect(reuse_if_open=True)
    ensure_migrations_applied()
    yield
    if not db.is_closed():
        db.close()


@dataclass
class ServiceTestContext:
    project_ids: set[UUID] = field(default_factory=set)

    def create_project_model(
        self,
        *,
        name: str | None = None,
        description: str | None = "Service test project",
    ) -> ResearchProject:
        project = ResearchProject.create(
            id=uuid4(),
            name=name or f"Service Test Project {uuid4()}",
            description=description,
        )
        self.track_project(cast(UUID, project.id))
        return project

    def track_project(self, project_id: UUID) -> None:
        self.project_ids.add(project_id)

    def _payload_project_id(self, payload: object) -> UUID | None:
        if not isinstance(payload, dict):
            return None

        project_id = payload.get("project_id")
        if isinstance(project_id, UUID):
            return project_id

        if isinstance(project_id, str):
            try:
                return UUID(project_id)
            except ValueError:
                return None

        return None

    def cleanup(self) -> None:
        if not self.project_ids:
            return

        for job in ProcessingJob.select():
            payload = job.payload or {}
            if self._payload_project_id(payload) in self.project_ids:
                job.delete_instance()

        for project_id in self.project_ids:
            project = ResearchProject.get_or_none(ResearchProject.id == project_id)
            if project is not None:
                project.delete_instance(recursive=True)


@pytest.fixture()
def service_context(migrated_db):
    context = ServiceTestContext()
    yield context
    context.cleanup()
