from typing import Any
from uuid import UUID, uuid4

from app.models.base.base_model import db
from app.models.document.document_model import Document
from app.models.project.project_model import ResearchProject


class DocumentRepository:
    def create(
        self,
        *,
        project: ResearchProject,
        title: str,
        original_filename: str,
        storage_path: str,
        status: str = "registered",
        metadata: dict[str, Any] | None = None,
    ) -> Document:
        with db.atomic():
            return Document.create(
                id=uuid4(),
                project=project,
                title=title,
                original_filename=original_filename,
                storage_path=storage_path,
                status=status,
                metadata=metadata,
            )

    def list_for_project(self, project_id: UUID) -> list[Document]:
        return list(
            Document.select()
            .where(Document.project == project_id)
            .order_by(Document.created_at.desc())
        )

    def get(self, document_id: UUID) -> Document | None:
        return Document.get_or_none(Document.id == document_id)

    def update(self, document: Document, values: dict[str, Any]) -> Document:
        for field_name, value in values.items():
            setattr(document, field_name, value)

        with db.atomic():
            document.save()
        return document

    def delete(self, document: Document) -> int:
        with db.atomic():
            return document.delete_instance(recursive=True)
