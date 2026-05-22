from typing import NoReturn
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.services.project.project_service import (
    ProjectCreatePayload,
    ProjectNotFoundError,
    ProjectRead,
    ProjectService,
    ProjectServiceError,
    ProjectUpdatePayload,
    ProjectValidationError,
)


project_router = APIRouter(prefix="/projects", tags=["projects"])
project_service = ProjectService()


def _raise_project_http_error(exc: Exception) -> NoReturn:
    if isinstance(exc, ProjectValidationError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.detail) from exc
    if isinstance(exc, ProjectNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail) from exc
    if isinstance(exc, ProjectServiceError):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=exc.detail) from exc
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="unexpected project service error") from exc


@project_router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreatePayload) -> ProjectRead:
    try:
        return project_service.create_project(payload)
    except ProjectServiceError as exc:
        _raise_project_http_error(exc)


@project_router.get("", response_model=list[ProjectRead])
def list_projects() -> list[ProjectRead]:
    try:
        return project_service.list_projects()
    except ProjectServiceError as exc:
        _raise_project_http_error(exc)


@project_router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: UUID) -> ProjectRead:
    try:
        return project_service.get_project(project_id)
    except ProjectServiceError as exc:
        _raise_project_http_error(exc)


@project_router.patch("/{project_id}", response_model=ProjectRead)
def update_project(project_id: UUID, payload: ProjectUpdatePayload) -> ProjectRead:
    try:
        return project_service.update_project(project_id, payload)
    except ProjectServiceError as exc:
        _raise_project_http_error(exc)
