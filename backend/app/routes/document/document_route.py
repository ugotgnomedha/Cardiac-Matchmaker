from typing import NoReturn
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.services.document.document_service import (
    DocumentCreatePayload,
    DocumentRead,
    DocumentService,
    DocumentServiceError,
)
from app.services.project.project_service import ProjectNotFoundError


document_router = APIRouter(prefix="/projects/{project_id}/documents", tags=["documents"])
document_service = DocumentService()


def _raise_document_http_error(exc: Exception) -> NoReturn:
    if isinstance(exc, ProjectNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail) from exc
    if isinstance(exc, DocumentServiceError):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=exc.detail) from exc
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="unexpected document service error") from exc


@document_router.post("", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
def create_document(project_id: UUID, payload: DocumentCreatePayload) -> DocumentRead:
    try:
        return document_service.create_document(project_id, payload)
    except (DocumentServiceError, ProjectNotFoundError) as exc:
        _raise_document_http_error(exc)


@document_router.get("", response_model=list[DocumentRead])
def list_documents(project_id: UUID) -> list[DocumentRead]:
    try:
        return document_service.list_documents(project_id)
    except (DocumentServiceError, ProjectNotFoundError) as exc:
        _raise_document_http_error(exc)
