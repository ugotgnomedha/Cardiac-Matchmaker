import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.document.document_model import Document
from app.repositories.document_repository import DocumentRepository
from app.services.project.project_service import ProjectService


class DocumentServiceError(Exception):
    def __init__(self, detail: Any):
        super().__init__(str(detail))
        self.detail = detail


class DocumentCreatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=255)
    original_filename: str = Field(min_length=1, max_length=255)
    storage_path: str = Field(min_length=1)
    status: str = Field(default="registered", min_length=1, max_length=50)
    metadata: dict[str, Any] | None = None


class DocumentRead(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    original_filename: str
    storage_path: str
    status: str
    metadata: dict[str, Any] | None
    created_at: datetime.datetime
    updated_at: datetime.datetime


class DocumentService:
    def __init__(self) -> None:
        self.project_service = ProjectService()
        self.document_repository = DocumentRepository()

    def create_document(self, project_id: UUID, payload: DocumentCreatePayload) -> DocumentRead:
        project = self.project_service.get_project_model(project_id)

        document = self.document_repository.create(
            project=project,
            title=payload.title,
            original_filename=payload.original_filename,
            storage_path=payload.storage_path,
            status=payload.status,
            metadata=payload.metadata,
        )
        return self._to_read_model(document)

    def delete_document(self, project_id: UUID, document_id: UUID) -> None:
        self.project_service.get_project_model(project_id)
        document = self.document_repository.get(document_id)
        if document is None:
            raise DocumentServiceError(f"document {document_id} not found")
        try:
            from app.services.analysis.rag_store import QdrantVectorStore
            QdrantVectorStore().delete_by_document(str(document_id))
        except Exception:
            pass
        self.document_repository.delete(document)

    def list_documents(self, project_id: UUID) -> list[DocumentRead]:
        self.project_service.get_project_model(project_id)
        return [self._to_read_model(document) for document in self.document_repository.list_for_project(project_id)]

    def _to_read_model(self, document: Document) -> DocumentRead:
        return DocumentRead(
            id=getattr(document, "id"),
            project_id=getattr(document, "project_id"),
            title=getattr(document, "title"),
            original_filename=getattr(document, "original_filename"),
            storage_path=getattr(document, "storage_path"),
            status=getattr(document, "status"),
            metadata=getattr(document, "metadata"),
            created_at=getattr(document, "created_at"),
            updated_at=getattr(document, "updated_at"),
        )
