from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.models.evidence.evidence_model import EvidenceItem
from app.models.job.job_model import ProcessingJob
from app.models.report.report_model import Report
from app.models.run.run_model import AnalysisRun, AnalysisStep
from app.services.run.run_service import (
    ReportNotFoundError,
    RunCreatePayload,
    RunNotFoundError,
    RunService,
)


def make_run_payload(
    *,
    target_application: str = "myocardial patch",
    target_tissue: str = "left ventricle",
) -> RunCreatePayload:
    return RunCreatePayload(
        target_application=target_application,
        target_tissue=target_tissue,
        query="Find placental material for myocardial patch support.",
        constraints={"max_candidates": 5},
    )


def test_run_service_creates_queued_run_job_and_lists_by_project(service_context):
    project = service_context.create_project_model()
    other_project = service_context.create_project_model()
    service = RunService()

    run = service.create_run(project.id, make_run_payload())
    service.create_run(other_project.id, make_run_payload(target_tissue="right ventricle"))

    project_runs = service.list_project_runs(project.id)
    queued_jobs = [
        job
        for job in ProcessingJob.select().where(
            ProcessingJob.job_type == "analysis_run",
            ProcessingJob.status == "queued",
        )
        if job.payload and job.payload.get("analysis_run_id") == str(run.id)
    ]

    assert run.status == "queued"
    assert run.project_id == project.id
    assert [project_run.id for project_run in project_runs] == [run.id]
    assert len(queued_jobs) == 1
    assert queued_jobs[0].payload["project_id"] == str(project.id)


def test_run_service_returns_ordered_steps_evidence_and_latest_report(service_context):
    project = service_context.create_project_model()
    service = RunService()
    run = service.create_run(project.id, make_run_payload())
    run_model = AnalysisRun.get_by_id(run.id)

    AnalysisStep.create(
        analysis_run=run_model,
        sequence_number=2,
        step_name="retrieve_literature",
        status="done",
        output_snapshot={"chunks": 3},
    )
    AnalysisStep.create(
        analysis_run=run_model,
        sequence_number=1,
        step_name="align_data",
        status="done",
        output_snapshot={"method": "baseline"},
    )
    evidence = EvidenceItem.create(
        analysis_run=run_model,
        candidate_name="Amnion",
        claim="Extracellular matrix support is relevant to myocardial patch use.",
        support_label="supports",
        score=0.82,
        metadata={"retrieval_query": "amnion extracellular matrix"},
    )
    Report.create(
        analysis_run=run_model,
        status="draft",
        json_body={"version": 1},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    Report.create(
        analysis_run=run_model,
        status="ready",
        json_body={"version": 2},
        markdown_body="# Ready report",
        created_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )

    steps = service.list_steps(run.id)
    evidence_items = service.list_evidence(run.id)
    latest_report = service.get_report(run.id)

    assert [step.step_name for step in steps] == ["align_data", "retrieve_literature"]
    assert evidence_items[0].id == evidence.id
    assert evidence_items[0].metadata == {"retrieval_query": "amnion extracellular matrix"}
    assert latest_report.status == "ready"
    assert latest_report.json_body == {"version": 2}


def test_run_service_raises_for_missing_run_and_missing_report(service_context):
    service = RunService()
    missing_run_id = uuid4()

    with pytest.raises(RunNotFoundError, match=str(missing_run_id)):
        service.get_run(missing_run_id)

    project = service_context.create_project_model()
    run = service.create_run(project.id, make_run_payload())

    with pytest.raises(ReportNotFoundError, match=str(run.id)):
        service.get_report(run.id)
