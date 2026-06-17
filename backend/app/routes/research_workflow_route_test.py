from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

import app.main as main_module
import app.routes.dataset.dataset_route as dataset_route_module
import app.routes.document.document_route as document_route_module
import app.routes.project.project_route as project_route_module
import app.routes.run.run_route as run_route_module
from app.main import app
from app.services.dataset.dataset_service import DatasetRead
from app.services.document.document_service import DocumentRead
from app.services.project.project_service import ProjectNotFoundError, ProjectRead
from app.services.run.run_service import AnalysisRunRead, ReportNotFoundError


def make_user() -> SimpleNamespace:
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=uuid4(),
        email="researcher@example.com",
        is_active=True,
        is_superuser=False,
        created_at=now,
        updated_at=now,
    )


def make_project_read(project_id: UUID | None = None) -> ProjectRead:
    now = datetime.now(timezone.utc)
    return ProjectRead(
        id=project_id or uuid4(),
        name="Cardiac MVP",
        description="Demo research workflow",
        created_at=now,
        updated_at=now,
    )


def make_dataset_read(project_id: UUID) -> DatasetRead:
    now = datetime.now(timezone.utc)
    return DatasetRead(
        id=uuid4(),
        project_id=project_id,
        name="Placenta proteomics",
        type="placenta",
        original_filename="placenta.tsv",
        storage_path="/data/raw/placenta.tsv",
        metadata={"delimiter": "tab"},
        created_at=now,
        updated_at=now,
    )


def make_document_read(project_id: UUID) -> DocumentRead:
    now = datetime.now(timezone.utc)
    return DocumentRead(
        id=uuid4(),
        project_id=project_id,
        title="Heart Map",
        original_filename="heart-map.pdf",
        storage_path="/data/pdfs/heart-map.pdf",
        status="registered",
        metadata={"paper": "Doll et al."},
        created_at=now,
        updated_at=now,
    )


def make_run_read(project_id: UUID) -> AnalysisRunRead:
    now = datetime.now(timezone.utc)
    return AnalysisRunRead(
        id=uuid4(),
        project_id=project_id,
        application_query_id=uuid4(),
        status="queued",
        query="Find placental material for myocardial patch support.",
        target_application="myocardial patch",
        target_tissue="left ventricle",
        function_target=None,
        constraints={"max_candidates": 5},
        selected_config=None,
        started_at=None,
        finished_at=None,
        error_message=None,
        created_at=now,
        updated_at=now,
    )


def authorize_requests(monkeypatch) -> None:
    monkeypatch.setattr(main_module.auth_service, "verify_access_token", lambda *_args, **_kwargs: make_user())


def test_projects_are_auth_protected() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/projects")

    assert response.status_code == 401
    assert response.json() == {"detail": "Unauthorized"}


def test_project_routes_create_list_get_and_patch(monkeypatch) -> None:
    authorize_requests(monkeypatch)
    project = make_project_read()
    updated_project = project.model_copy(update={"description": "Updated"})

    monkeypatch.setattr(project_route_module.project_service, "create_project", lambda _payload: project)
    monkeypatch.setattr(project_route_module.project_service, "list_projects", lambda: [project])
    monkeypatch.setattr(project_route_module.project_service, "get_project", lambda _project_id: project)
    monkeypatch.setattr(project_route_module.project_service, "update_project", lambda _project_id, _payload: updated_project)

    with TestClient(app) as client:
        client.cookies.set("access_token", "test-access-token")
        create_response = client.post(
            "/api/v1/projects",
            json={"name": "Cardiac MVP", "description": "Demo research workflow"},
        )
        list_response = client.get("/api/v1/projects")
        get_response = client.get(f"/api/v1/projects/{project.id}")
        patch_response = client.patch(f"/api/v1/projects/{project.id}", json={"description": "Updated"})

    assert create_response.status_code == 201
    assert create_response.json()["id"] == str(project.id)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert get_response.status_code == 200
    assert get_response.json()["name"] == project.name
    assert patch_response.status_code == 200
    assert patch_response.json()["description"] == "Updated"


def test_project_create_rejects_bad_payload(monkeypatch) -> None:
    authorize_requests(monkeypatch)

    with TestClient(app) as client:
        client.cookies.set("access_token", "test-access-token")
        response = client.post("/api/v1/projects", json={"description": "Missing name"})

    assert response.status_code == 422


def test_dataset_and_document_registration_routes(monkeypatch) -> None:
    authorize_requests(monkeypatch)
    project_id = uuid4()
    dataset = make_dataset_read(project_id)
    document = make_document_read(project_id)

    monkeypatch.setattr(dataset_route_module.dataset_service, "create_dataset", lambda _project_id, _payload: dataset)
    monkeypatch.setattr(dataset_route_module.dataset_service, "list_datasets", lambda _project_id: [dataset])
    monkeypatch.setattr(document_route_module.document_service, "create_document", lambda _project_id, _payload: document)
    monkeypatch.setattr(document_route_module.document_service, "list_documents", lambda _project_id: [document])

    with TestClient(app) as client:
        client.cookies.set("access_token", "test-access-token")
        dataset_create_response = client.post(
            f"/api/v1/projects/{project_id}/datasets",
            json={
                "name": "Placenta proteomics",
                "type": "placenta",
                "original_filename": "placenta.tsv",
                "storage_path": "/data/raw/placenta.tsv",
                "metadata": {"delimiter": "tab"},
            },
        )
        dataset_list_response = client.get(f"/api/v1/projects/{project_id}/datasets")
        document_create_response = client.post(
            f"/api/v1/projects/{project_id}/documents",
            json={
                "title": "Heart Map",
                "original_filename": "heart-map.pdf",
                "storage_path": "/data/pdfs/heart-map.pdf",
                "metadata": {"paper": "Doll et al."},
            },
        )
        document_list_response = client.get(f"/api/v1/projects/{project_id}/documents")

    assert dataset_create_response.status_code == 201
    assert dataset_create_response.json()["project_id"] == str(project_id)
    assert dataset_list_response.status_code == 200
    assert dataset_list_response.json()[0]["name"] == dataset.name
    assert document_create_response.status_code == 201
    assert document_create_response.json()["status"] == "registered"
    assert document_list_response.status_code == 200
    assert document_list_response.json()[0]["title"] == document.title


def test_dataset_routes_return_404_for_missing_project(monkeypatch) -> None:
    authorize_requests(monkeypatch)
    project_id = uuid4()

    def raise_missing_project(_project_id):
        raise ProjectNotFoundError(f"project {project_id} not found")

    monkeypatch.setattr(dataset_route_module.dataset_service, "list_datasets", raise_missing_project)

    with TestClient(app) as client:
        client.cookies.set("access_token", "test-access-token")
        response = client.get(f"/api/v1/projects/{project_id}/datasets")

    assert response.status_code == 404
    assert response.json() == {"detail": f"project {project_id} not found"}


def test_run_lifecycle_routes(monkeypatch) -> None:
    authorize_requests(monkeypatch)
    project_id = uuid4()
    run = make_run_read(project_id)

    monkeypatch.setattr(run_route_module.run_service, "create_run", lambda _project_id, _payload: run)
    monkeypatch.setattr(run_route_module.run_service, "list_project_runs", lambda _project_id: [run])
    monkeypatch.setattr(run_route_module.run_service, "get_run", lambda _run_id: run)
    monkeypatch.setattr(run_route_module.run_service, "list_steps", lambda _run_id: [])
    monkeypatch.setattr(run_route_module.run_service, "list_evidence", lambda _run_id: [])

    with TestClient(app) as client:
        client.cookies.set("access_token", "test-access-token")
        create_response = client.post(
            f"/api/v1/projects/{project_id}/runs",
            json={
                "target_application": "myocardial patch",
                "target_tissue": "left ventricle",
                "query": "Find placental material for myocardial patch support.",
                "constraints": {"max_candidates": 5},
            },
        )
        list_response = client.get(f"/api/v1/projects/{project_id}/runs")
        detail_response = client.get(f"/api/v1/runs/{run.id}")
        steps_response = client.get(f"/api/v1/runs/{run.id}/steps")
        evidence_response = client.get(f"/api/v1/runs/{run.id}/evidence")

    assert create_response.status_code == 201
    assert create_response.json()["status"] == "queued"
    assert list_response.status_code == 200
    assert list_response.json()[0]["id"] == str(run.id)
    assert detail_response.status_code == 200
    assert detail_response.json()["target_tissue"] == "left ventricle"
    assert steps_response.status_code == 200
    assert steps_response.json() == []
    assert evidence_response.status_code == 200
    assert evidence_response.json() == []


def test_run_report_route_returns_404_before_report_exists(monkeypatch) -> None:
    authorize_requests(monkeypatch)
    run_id = uuid4()

    def raise_missing_report(_run_id):
        raise ReportNotFoundError(f"report for run {run_id} not found")

    monkeypatch.setattr(run_route_module.run_service, "get_report", raise_missing_report)

    with TestClient(app) as client:
        client.cookies.set("access_token", "test-access-token")
        response = client.get(f"/api/v1/runs/{run_id}/report")

    assert response.status_code == 404
    assert response.json() == {"detail": f"report for run {run_id} not found"}
