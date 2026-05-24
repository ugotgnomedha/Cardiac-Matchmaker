from uuid import uuid4

import pytest

from app.models.document.document_model import Document
from app.services.document.document_service import DocumentCreatePayload, DocumentService
from app.services.project.project_service import ProjectNotFoundError


def make_document_payload(
    *,
    title: str = "Heart Map",
    storage_path: str = "/data/pdfs/heart-map.pdf",
    status: str = "registered",
) -> DocumentCreatePayload:
    return DocumentCreatePayload(
        title=title,
        original_filename=storage_path.rsplit("/", maxsplit=1)[-1],
        storage_path=storage_path,
        status=status,
        metadata={"paper": title, "source": "service-test"},
    )


def test_document_service_creates_document_with_project_scope(service_context):
    project = service_context.create_project_model()
    other_project = service_context.create_project_model()
    service = DocumentService()

    heart_map = service.create_document(
        project.id,
        make_document_payload(title="Heart Map", storage_path="/data/pdfs/heart-map.pdf"),
    )
    placenta_review = service.create_document(
        project.id,
        make_document_payload(title="Placenta Review", storage_path="/data/pdfs/placenta.pdf"),
    )
    service.create_document(
        other_project.id,
        make_document_payload(title="Other Project Paper", storage_path="/data/pdfs/other.pdf"),
    )

    project_documents = service.list_documents(project.id)
    project_document_ids = {document.id for document in project_documents}

    assert project_document_ids == {heart_map.id, placenta_review.id}
    assert all(document.project_id == project.id for document in project_documents)
    assert heart_map.status == "registered"


def test_document_service_persists_document_row(service_context):
    project = service_context.create_project_model()

    created_document = DocumentService().create_document(
        project.id,
        make_document_payload(
            title="Indexed Heart Map",
            storage_path="/data/pdfs/indexed-heart-map.pdf",
            status="indexed",
        ),
    )

    persisted_document = Document.get_by_id(created_document.id)
    assert persisted_document.project.id == project.id
    assert persisted_document.title == "Indexed Heart Map"
    assert persisted_document.status == "indexed"


def test_document_service_raises_for_missing_project(migrated_db):
    missing_project_id = uuid4()

    with pytest.raises(ProjectNotFoundError, match=str(missing_project_id)):
        DocumentService().list_documents(missing_project_id)
