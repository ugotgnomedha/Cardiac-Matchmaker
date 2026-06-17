from typing import Any
from uuid import uuid4

from app.models.base.base_model import db
from app.models.job.job_model import ProcessingJob


class ProcessingJobRepository:
    def create(
        self,
        *,
        job_type: str,
        status: str = "queued",
        payload: dict[str, Any] | None = None,
    ) -> ProcessingJob:
        with db.atomic():
            return ProcessingJob.create(
                id=uuid4(),
                job_type=job_type,
                status=status,
                payload=payload,
            )
