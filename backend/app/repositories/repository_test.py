from typing import cast
from uuid import UUID

from app.models.job.job_model import ProcessingJob
from app.repositories.dataset_repository import DatasetRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.evidence_repository import CandidateRepository, EvidenceRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.report_repository import ReportRepository
from app.repositories.run_repository import RunRepository


def test_repositories_create_read_update_and_list_core_workflow(service_context):
    project_repository = ProjectRepository()
    dataset_repository = DatasetRepository()
    document_repository = DocumentRepository()
    run_repository = RunRepository()
    candidate_repository = CandidateRepository()
    evidence_repository = EvidenceRepository()
    report_repository = ReportRepository()

    project = project_repository.create(name="Repository Layer", description="CRUD smoke test")
    service_context.track_project(project.id)
    project_repository.update(project, {"description": "Updated"})

    dataset = dataset_repository.create(
        project=project,
        name="Placenta proteomics",
        type="placenta",
        original_filename="placenta.tsv",
        storage_path="/data/raw/placenta.tsv",
        metadata={"delimiter": "tab"},
    )
    document = document_repository.create(
        project=project,
        title="Heart Map",
        original_filename="heart-map.pdf",
        storage_path="/data/pdfs/heart-map.pdf",
        metadata={"paper": "Heart Map"},
    )
    run = run_repository.create_with_query_and_job(
        project=project,
        query_text="Find placental material for myocardial patch support.",
        target_application="myocardial patch",
        target_tissue="left ventricle",
        constraints={"max_candidates": 5},
        selected_config={"method": "cca"},
    )
    candidate = candidate_repository.create(
        analysis_run=run,
        rank=1,
        candidate_name="Amnion",
        target_name="left ventricle",
        score=0.81,
        method="cca",
    )
    evidence = evidence_repository.create(
        analysis_run=run,
        candidate_match=candidate,
        candidate_name="Amnion",
        claim="Extracellular matrix support is relevant.",
        support_label="supports",
        score=0.9,
    )
    report = report_repository.create(
        analysis_run=run,
        status="ready",
        json_body={"top_candidate": "Amnion"},
        markdown_body="# Ready report",
    )

    project_id = cast(UUID, project.id)
    run_id = cast(UUID, run.id)

    fetched_project = project_repository.get(project_id)
    latest_report = report_repository.get_latest_for_run(run_id)

    assert fetched_project is not None
    assert latest_report is not None
    assert fetched_project.description == "Updated"
    assert dataset_repository.list_for_project(project_id)[0].id == dataset.id
    assert document_repository.list_for_project(project_id)[0].id == document.id
    assert run_repository.list_for_project(project_id)[0].id == run.id
    assert candidate_repository.list_for_run(run_id)[0].id == candidate.id
    assert evidence_repository.list_for_run(run_id)[0].id == evidence.id
    assert latest_report.id == report.id
    assert ProcessingJob.get(ProcessingJob.payload["analysis_run_id"] == str(run_id)).status == "queued"
