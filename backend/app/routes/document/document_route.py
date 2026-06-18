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
        detail = str(exc.detail)
        status_code = status.HTTP_404_NOT_FOUND if "not found" in detail else status.HTTP_500_INTERNAL_SERVER_ERROR
        raise HTTPException(status_code=status_code, detail=detail) from exc
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


@document_router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(project_id: UUID, document_id: UUID) -> None:
    try:
        document_service.delete_document(project_id, document_id)
    except (DocumentServiceError, ProjectNotFoundError) as exc:
        _raise_document_http_error(exc)


@document_router.post("/{document_id}/index")
def index_document(project_id: UUID, document_id: UUID):
    try:
        document_service.project_service.get_project_model(project_id)
    except ProjectNotFoundError as exc:
        _raise_document_http_error(exc)

    from uuid import uuid4
    from app.models.base.base_model import db
    from app.models.document.document_model import Document
    from app.models.job.job_model import ProcessingJob

    document = Document.get_or_none(Document.id == document_id)
    if document is None or getattr(document, "project_id") != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"document {document_id} not found")

    with db.atomic():
        document.status = "indexing"
        document.save()
        ProcessingJob.create(
            id=uuid4(),
            job_type="index_document",
            status="queued",
            payload={"document_id": str(document_id)},
        )

    return {"status": "queued"}
