"""Background worker that claims queued analysis_run jobs and advances them through a placeholder step.

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
from app.models.run.run_model import AnalysisRun, AnalysisStep

JOB_TYPE_ANALYSIS_RUN = "analysis_run"
POLL_INTERVAL_SECONDS = float(os.getenv("WORKER_POLL_INTERVAL", "5"))


def utc_now() -> datetime.datetime:
    """Current UTC time."""
    return datetime.datetime.now(datetime.timezone.utc)


def claim_next_job() -> ProcessingJob | None:
    """Atomically claim the oldest queued analysis job (FOR UPDATE SKIP LOCKED)."""
    with db.atomic():
        job = (
            ProcessingJob.select()
            .where(
                ProcessingJob.status == "queued",
                ProcessingJob.job_type == JOB_TYPE_ANALYSIS_RUN,
            )
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


def handle_analysis_run(run: AnalysisRun) -> None:
    """Advance the run through one bookkeeping step (placeholder for the pipeline)."""
    AnalysisStep.create(
        analysis_run=run,
        sequence_number=0,
        step_name="initialize",
        status="completed",
        started_at=utc_now(),
        finished_at=utc_now(),
        output_snapshot={"note": "analysis pipeline not yet wired"},
    )


def process_job(job: ProcessingJob) -> None:
    """Execute a claimed job and reconcile both the job and its run."""
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


def run_forever(poll_interval: float = POLL_INTERVAL_SECONDS) -> None:
    """Poll for queued analysis jobs forever, processing them as they appear."""
    print(f"Worker started; polling for '{JOB_TYPE_ANALYSIS_RUN}' jobs every {poll_interval}s.")
    while True:
        try:
            with db.connection_context():
                job = claim_next_job()
                if job is not None:
                    print(f"Processing job {job.id} (run {_run_id_from_job(job)}).")
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
