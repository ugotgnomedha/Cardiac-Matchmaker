from typing import NoReturn
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.services.dataset.dataset_service import (
    DatasetCreatePayload,
    DatasetRead,
    DatasetService,
    DatasetServiceError,
    DatasetUpdatePayload,
)
from app.services.project.project_service import ProjectNotFoundError


dataset_router = APIRouter(prefix="/projects/{project_id}/datasets", tags=["datasets"])
dataset_service = DatasetService()


def _raise_dataset_http_error(exc: Exception) -> NoReturn:
    if isinstance(exc, ProjectNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail) from exc
    if isinstance(exc, DatasetServiceError):
        detail = str(exc.detail)
        status_code = (
            status.HTTP_404_NOT_FOUND if "not found" in detail
            else status.HTTP_422_UNPROCESSABLE_ENTITY if detail.startswith("file not found") or detail.startswith("no fields")
            else status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        raise HTTPException(status_code=status_code, detail=detail) from exc
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="unexpected dataset service error") from exc


@dataset_router.post("", response_model=DatasetRead, status_code=status.HTTP_201_CREATED)
def create_dataset(project_id: UUID, payload: DatasetCreatePayload) -> DatasetRead:
    try:
        return dataset_service.create_dataset(project_id, payload)
    except (DatasetServiceError, ProjectNotFoundError) as exc:
        _raise_dataset_http_error(exc)


@dataset_router.get("", response_model=list[DatasetRead])
def list_datasets(project_id: UUID) -> list[DatasetRead]:
    try:
        return dataset_service.list_datasets(project_id)
    except (DatasetServiceError, ProjectNotFoundError) as exc:
        _raise_dataset_http_error(exc)


@dataset_router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dataset(project_id: UUID, dataset_id: UUID) -> None:
    try:
        dataset_service.delete_dataset(project_id, dataset_id)
    except (DatasetServiceError, ProjectNotFoundError) as exc:
        _raise_dataset_http_error(exc)


@dataset_router.put("/{dataset_id}", response_model=DatasetRead)
def update_dataset(project_id: UUID, dataset_id: UUID, payload: DatasetUpdatePayload) -> DatasetRead:
    try:
        return dataset_service.update_dataset(project_id, dataset_id, payload)
    except (DatasetServiceError, ProjectNotFoundError) as exc:
        _raise_dataset_http_error(exc)
