from typing import NoReturn
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.services.project.project_service import ProjectNotFoundError
from app.services.run.run_service import (
    AnalysisRunRead,
    AnalysisStepRead,
    CandidateMatchRead,
    EvidenceItemRead,
    ReportNotFoundError,
    ReportRead,
    RunCreatePayload,
    RunNotFoundError,
    RunService,
    RunServiceError,
)


run_router = APIRouter(tags=["runs"])
run_service = RunService()


def _raise_run_http_error(exc: Exception) -> NoReturn:
    if isinstance(exc, (ProjectNotFoundError, RunNotFoundError, ReportNotFoundError)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail) from exc
    if isinstance(exc, RunServiceError):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=exc.detail) from exc
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="unexpected run service error") from exc


@run_router.post("/projects/{project_id}/runs", response_model=AnalysisRunRead, status_code=status.HTTP_201_CREATED)
def create_run(project_id: UUID, payload: RunCreatePayload) -> AnalysisRunRead:
    try:
        return run_service.create_run(project_id, payload)
    except (ProjectNotFoundError, RunServiceError) as exc:
        _raise_run_http_error(exc)


@run_router.get("/projects/{project_id}/runs", response_model=list[AnalysisRunRead])
def list_project_runs(project_id: UUID) -> list[AnalysisRunRead]:
    try:
        return run_service.list_project_runs(project_id)
    except (ProjectNotFoundError, RunServiceError) as exc:
        _raise_run_http_error(exc)


@run_router.get("/runs/{run_id}", response_model=AnalysisRunRead)
def get_run(run_id: UUID) -> AnalysisRunRead:
    try:
        return run_service.get_run(run_id)
    except RunServiceError as exc:
        _raise_run_http_error(exc)


@run_router.get("/runs/{run_id}/steps", response_model=list[AnalysisStepRead])
def list_steps(run_id: UUID) -> list[AnalysisStepRead]:
    try:
        return run_service.list_steps(run_id)
    except RunServiceError as exc:
        _raise_run_http_error(exc)


@run_router.get("/runs/{run_id}/evidence", response_model=list[EvidenceItemRead])
def list_evidence(run_id: UUID) -> list[EvidenceItemRead]:
    try:
        return run_service.list_evidence(run_id)
    except RunServiceError as exc:
        _raise_run_http_error(exc)


@run_router.get("/runs/{run_id}/candidates", response_model=list[CandidateMatchRead])
def list_candidates(run_id: UUID) -> list[CandidateMatchRead]:
    try:
        return run_service.list_candidates(run_id)
    except RunServiceError as exc:
        _raise_run_http_error(exc)


@run_router.get("/runs/{run_id}/report", response_model=ReportRead)
def get_report(run_id: UUID) -> ReportRead:
    try:
        return run_service.get_report(run_id)
    except RunServiceError as exc:
        _raise_run_http_error(exc)
