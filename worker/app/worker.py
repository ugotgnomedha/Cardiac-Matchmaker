"""Background worker that claims queued jobs and executes them.

Shares the backend's Peewee models via the mounted ``/app/backend`` (see ``compose.yml``),
falling back to the sibling ``backend`` directory locally.
"""

import datetime
import os
import sys
import time
import traceback
from pathlib import Path


def _add_backend_to_path() -> None:
    """Put the backend package on ``sys.path`` so ``app.models`` is importable."""
    candidates = [
        os.getenv("BACKEND_PATH"),
        "/app/backend",
        str(Path(__file__).resolve().parents[2] / "backend"),
    ]
    for candidate in candidates:
        if candidate and (Path(candidate) / "app").is_dir():
            if candidate not in sys.path:
                sys.path.insert(0, candidate)
            return
    raise RuntimeError(
        "Could not locate the backend package. Set BACKEND_PATH to the directory "
        "that contains the 'app' package."
    )


_add_backend_to_path()

from app.models.base.base_model import db
from app.models.job.job_model import ProcessingJob
from app.models.run.run_model import AnalysisRun

POLL_INTERVAL_SECONDS = float(os.getenv("WORKER_POLL_INTERVAL", "5"))


def utc_now() -> datetime.datetime:
    """Current UTC time."""
    return datetime.datetime.now(datetime.timezone.utc)


def claim_next_job() -> ProcessingJob | None:
    """Atomically claim the oldest queued job of any type (FOR UPDATE SKIP LOCKED)."""
    with db.atomic():
        job = (
            ProcessingJob.select()
            .where(ProcessingJob.status == "queued")
            .order_by(ProcessingJob.created_at.asc())
            .for_update("FOR UPDATE SKIP LOCKED")
            .first()
        )
        if job is None:
            return None
        job.status = "running"
        job.attempts = (job.attempts or 0) + 1
        job.started_at = utc_now()
        job.save()
    return job


def _run_id_from_job(job: ProcessingJob) -> str | None:
    """Extract the analysis_run_id from a job's payload."""
    payload = job.payload or {}
    return payload.get("analysis_run_id")


def _document_id_from_job(job: ProcessingJob) -> str | None:
    """Extract the document_id from a job's payload."""
    payload = job.payload or {}
    return payload.get("document_id")


def handle_analysis_run(run: AnalysisRun) -> None:
    """Run the alignment/RAG/report pipeline, persisting steps/evidence/report."""
    from app.services.analysis.pipeline import AnalysisService

    AnalysisService().run(run)


def handle_index_document(document_id: str) -> None:
    """Index a document's PDF into Qdrant."""
    from app.models.document.document_model import Document
    from app.services.analysis.rag_store import LiteratureIndexer

    document = Document.get_or_none(Document.id == document_id)
    if document is None:
        raise ValueError(f"document {document_id} not found")

    LiteratureIndexer().index_document(document)


def process_job(job: ProcessingJob) -> None:
    """Execute a claimed job, dispatching by type."""
    if job.job_type == "analysis_run":
        _process_analysis_run_job(job)
    elif job.job_type == "index_document":
        _process_index_document_job(job)
    else:
        job.status = "failed"
        job.last_error = f"unknown job_type {job.job_type!r}"
        job.finished_at = utc_now()
        job.save()


def _process_analysis_run_job(job: ProcessingJob) -> None:
    """Execute an analysis_run job."""
    run_id = _run_id_from_job(job)
    run = AnalysisRun.get_or_none(AnalysisRun.id == run_id) if run_id else None
    if run is None:
        job.status = "failed"
        job.last_error = f"analysis_run {run_id!r} not found"
        job.finished_at = utc_now()
        job.save()
        return

    run.status = "running"
    run.started_at = utc_now()
    run.error_message = None
    run.save()

    try:
        handle_analysis_run(run)
    except Exception as exc:
        run.status = "failed"
        run.error_message = str(exc)
        run.finished_at = utc_now()
        run.save()
        job.status = "failed"
        job.last_error = "".join(traceback.format_exception_only(type(exc), exc)).strip()
        job.finished_at = utc_now()
        job.save()
        return

    run.status = "completed"
    run.finished_at = utc_now()
    run.save()
    job.status = "completed"
    job.finished_at = utc_now()
    job.save()


def _process_index_document_job(job: ProcessingJob) -> None:
    """Execute an index_document job."""
    document_id = _document_id_from_job(job)
    if not document_id:
        job.status = "failed"
        job.last_error = "document_id missing from payload"
        job.finished_at = utc_now()
        job.save()
        return

    from app.models.document.document_model import Document
    document = Document.get_or_none(Document.id == document_id)
    if document is None:
        job.status = "failed"
        job.last_error = f"document {document_id} not found"
        job.finished_at = utc_now()
        job.save()
        return

    document.status = "indexing"
    document.save()

    try:
        handle_index_document(document_id)
    except Exception as exc:
        document.status = "failed"
        document.save()
        job.status = "failed"
        job.last_error = "".join(traceback.format_exception_only(type(exc), exc)).strip()
        job.finished_at = utc_now()
        job.save()
        return

    job.status = "completed"
    job.finished_at = utc_now()
    job.save()


def run_forever(poll_interval: float = POLL_INTERVAL_SECONDS) -> None:
    """Poll for queued jobs forever, processing them as they appear."""
    print("Worker started; polling for queued jobs.")
    while True:
        try:
            with db.connection_context():
                job = claim_next_job()
                if job is not None:
                    print(f"Processing job {job.id} (type={job.job_type}).")
                    process_job(job)
                    continue
        except Exception:
            traceback.print_exc()
        time.sleep(poll_interval)


def main() -> None:
    """Entry point: start the polling loop."""
    run_forever()


if __name__ == "__main__":
    main()
