import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.models.base.base_model import db
from app.models.evidence.evidence_model import EvidenceItem
from app.models.job.job_model import ProcessingJob
from app.models.report.report_model import Report
from app.models.run.run_model import AnalysisRun, AnalysisStep
from app.services.project.project_service import ProjectService


class RunServiceError(Exception):
    def __init__(self, detail: Any):
        super().__init__(str(detail))
        self.detail = detail


class RunNotFoundError(RunServiceError):
    pass


class ReportNotFoundError(RunServiceError):
    pass


class RunCreatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    target_application: str = Field(min_length=1, max_length=255)
    target_tissue: str = Field(min_length=1, max_length=255)
    query: str = Field(min_length=1)
    constraints: dict[str, Any] | None = None


class AnalysisRunRead(BaseModel):
    id: UUID
    project_id: UUID
    status: str
    query: str
    target_application: str
    target_tissue: str
    constraints: dict[str, Any] | None
    started_at: datetime.datetime | None
    finished_at: datetime.datetime | None
    error_message: str | None
    created_at: datetime.datetime
    updated_at: datetime.datetime


class AnalysisStepRead(BaseModel):
    id: UUID
    analysis_run_id: UUID
    sequence_number: int
    step_name: str
    status: str
    input_snapshot: dict[str, Any] | None
    output_snapshot: dict[str, Any] | None
    started_at: datetime.datetime | None
    finished_at: datetime.datetime | None
    error_message: str | None
    created_at: datetime.datetime


class EvidenceItemRead(BaseModel):
    id: UUID
    analysis_run_id: UUID
    candidate_match_id: UUID | None
    candidate_name: str
    claim: str
    document_id: UUID | None
    document_chunk_id: UUID | None
    support_label: str
    score: float | None
    metadata: dict[str, Any] | None
    created_at: datetime.datetime


class ReportRead(BaseModel):
    id: UUID
    analysis_run_id: UUID
    status: str
    json_body: dict[str, Any] | None
    markdown_body: str | None
    storage_path: str | None
    created_at: datetime.datetime
    updated_at: datetime.datetime


class RunService:
    def __init__(self) -> None:
        self.project_service = ProjectService()

    def create_run(self, project_id: UUID, payload: RunCreatePayload) -> AnalysisRunRead:
        project = self.project_service.get_project_model(project_id)

        with db.atomic():
            run = AnalysisRun.create(
                id=uuid4(),
                project=project,
                status="queued",
                query=payload.query,
                target_application=payload.target_application,
                target_tissue=payload.target_tissue,
                constraints=payload.constraints,
            )
            ProcessingJob.create(
                id=uuid4(),
                job_type="analysis_run",
                status="queued",
                payload={
                    "analysis_run_id": str(getattr(run, "id")),
                    "project_id": str(project_id),
                },
            )

        return self._to_run_read_model(run)

    def list_project_runs(self, project_id: UUID) -> list[AnalysisRunRead]:
        self.project_service.get_project_model(project_id)
        runs = (
            AnalysisRun.select()
            .where(AnalysisRun.project == project_id)
            .order_by(AnalysisRun.created_at.desc())
        )
        return [self._to_run_read_model(run) for run in runs]

    def get_run(self, run_id: UUID) -> AnalysisRunRead:
        return self._to_run_read_model(self.get_run_model(run_id))

    def list_steps(self, run_id: UUID) -> list[AnalysisStepRead]:
        self.get_run_model(run_id)
        steps = (
            AnalysisStep.select()
            .where(AnalysisStep.analysis_run == run_id)
            .order_by(AnalysisStep.sequence_number.asc(), AnalysisStep.created_at.asc())
        )
        return [self._to_step_read_model(step) for step in steps]

    def list_evidence(self, run_id: UUID) -> list[EvidenceItemRead]:
        self.get_run_model(run_id)
        evidence_items = (
            EvidenceItem.select()
            .where(EvidenceItem.analysis_run == run_id)
            .order_by(EvidenceItem.created_at.asc())
        )
        return [self._to_evidence_read_model(evidence_item) for evidence_item in evidence_items]

    def get_report(self, run_id: UUID) -> ReportRead:
        self.get_run_model(run_id)
        report = (
            Report.select()
            .where(Report.analysis_run == run_id)
            .order_by(Report.created_at.desc())
            .first()
        )
        if report is None:
            raise ReportNotFoundError(f"report for run {run_id} not found")

        return self._to_report_read_model(report)

    def get_run_model(self, run_id: UUID) -> AnalysisRun:
        run = AnalysisRun.get_or_none(AnalysisRun.id == run_id)
        if run is None:
            raise RunNotFoundError(f"run {run_id} not found")
        return run

    def _to_run_read_model(self, run: AnalysisRun) -> AnalysisRunRead:
        return AnalysisRunRead(
            id=getattr(run, "id"),
            project_id=getattr(run, "project_id"),
            status=getattr(run, "status"),
            query=getattr(run, "query"),
            target_application=getattr(run, "target_application"),
            target_tissue=getattr(run, "target_tissue"),
            constraints=getattr(run, "constraints"),
            started_at=getattr(run, "started_at"),
            finished_at=getattr(run, "finished_at"),
            error_message=getattr(run, "error_message"),
            created_at=getattr(run, "created_at"),
            updated_at=getattr(run, "updated_at"),
        )

    def _to_step_read_model(self, step: AnalysisStep) -> AnalysisStepRead:
        return AnalysisStepRead(
            id=getattr(step, "id"),
            analysis_run_id=getattr(step, "analysis_run_id"),
            sequence_number=getattr(step, "sequence_number"),
            step_name=getattr(step, "step_name"),
            status=getattr(step, "status"),
            input_snapshot=getattr(step, "input_snapshot"),
            output_snapshot=getattr(step, "output_snapshot"),
            started_at=getattr(step, "started_at"),
            finished_at=getattr(step, "finished_at"),
            error_message=getattr(step, "error_message"),
            created_at=getattr(step, "created_at"),
        )

    def _to_evidence_read_model(self, evidence_item: EvidenceItem) -> EvidenceItemRead:
        return EvidenceItemRead(
            id=getattr(evidence_item, "id"),
            analysis_run_id=getattr(evidence_item, "analysis_run_id"),
            candidate_match_id=getattr(evidence_item, "candidate_match_id"),
            candidate_name=getattr(evidence_item, "candidate_name"),
            claim=getattr(evidence_item, "claim"),
            document_id=getattr(evidence_item, "document_id"),
            document_chunk_id=getattr(evidence_item, "document_chunk_id"),
            support_label=getattr(evidence_item, "support_label"),
            score=getattr(evidence_item, "score"),
            metadata=getattr(evidence_item, "metadata"),
            created_at=getattr(evidence_item, "created_at"),
        )

    def _to_report_read_model(self, report: Report) -> ReportRead:
        return ReportRead(
            id=getattr(report, "id"),
            analysis_run_id=getattr(report, "analysis_run_id"),
            status=getattr(report, "status"),
            json_body=getattr(report, "json_body"),
            markdown_body=getattr(report, "markdown_body"),
            storage_path=getattr(report, "storage_path"),
            created_at=getattr(report, "created_at"),
            updated_at=getattr(report, "updated_at"),
        )
