from uuid import uuid4

import pytest

from app.models.project.project_model import ResearchProject
from app.services.project.project_service import (
    ProjectCreatePayload,
    ProjectNotFoundError,
    ProjectService,
    ProjectUpdatePayload,
    ProjectValidationError,
)


def test_project_service_creates_gets_and_lists_project(service_context):
    service = ProjectService()

    created_project = service.create_project(
        ProjectCreatePayload(
            name="  Cardiac Matching Study  ",
            description="  Demo workflow  ",
        )
    )
    service_context.track_project(created_project.id)

    fetched_project = service.get_project(created_project.id)
    listed_project_ids = {project.id for project in service.list_projects()}

    assert created_project.name == "Cardiac Matching Study"
    assert created_project.description == "Demo workflow"
    assert fetched_project.id == created_project.id
    assert fetched_project.name == created_project.name
    assert fetched_project.description == created_project.description
    assert created_project.id in listed_project_ids


def test_project_service_updates_project_and_rejects_empty_update(service_context):
    project = service_context.create_project_model(name="Original Project")
    service = ProjectService()

    updated_project = service.update_project(
        project.id,
        ProjectUpdatePayload(name="Updated Project", description=None),
    )

    persisted_project = ResearchProject.get_by_id(project.id)
    assert updated_project.name == "Updated Project"
    assert updated_project.description is None
    assert persisted_project.name == "Updated Project"
    assert persisted_project.description is None

    with pytest.raises(ProjectValidationError, match="at least one field"):
        service.update_project(project.id, ProjectUpdatePayload())


def test_project_service_raises_for_missing_project(migrated_db):
    missing_project_id = uuid4()

    with pytest.raises(ProjectNotFoundError, match=str(missing_project_id)):
        ProjectService().get_project(missing_project_id)
