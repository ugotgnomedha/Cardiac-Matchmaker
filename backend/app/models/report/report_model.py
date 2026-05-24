import datetime
import uuid

from peewee import CharField, DateTimeField, ForeignKeyField, TextField, UUIDField
from playhouse.postgres_ext import JSONField

from app.models.base.base_model import BaseModel
from app.models.run.run_model import AnalysisRun


def utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


class Report(BaseModel):
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    analysis_run = ForeignKeyField(AnalysisRun, backref="reports", on_delete="CASCADE")
    status = CharField(max_length=50, default="draft")
    json_body = JSONField(null=True)
    markdown_body = TextField(null=True)
    storage_path = TextField(null=True)
    created_at = DateTimeField(default=utc_now)
    updated_at = DateTimeField(default=utc_now)

    def save(self, *args, **kwargs):
        self.updated_at = utc_now()  # pyrefly: ignore
        return super().save(*args, **kwargs)

    class Meta:  # pyrefly: ignore
        table_name = "report"
