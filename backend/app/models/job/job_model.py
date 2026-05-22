import datetime
import uuid

from peewee import CharField, DateTimeField, IntegerField, TextField, UUIDField
from playhouse.postgres_ext import JSONField

from app.models.base.base_model import BaseModel


def utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


class ProcessingJob(BaseModel):
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    job_type = CharField(max_length=100)
    status = CharField(max_length=50, default="queued")
    payload = JSONField(null=True)
    attempts = IntegerField(default=0)
    last_error = TextField(null=True)
    created_at = DateTimeField(default=utc_now)
    updated_at = DateTimeField(default=utc_now)
    started_at = DateTimeField(null=True)
    finished_at = DateTimeField(null=True)

    def save(self, *args, **kwargs):
        self.updated_at = utc_now()  # pyrefly: ignore
        return super().save(*args, **kwargs)

    class Meta:  # pyrefly: ignore
        table_name = "processing_job"
