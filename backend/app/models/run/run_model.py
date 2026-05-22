import datetime
import uuid

from peewee import (
    CharField,
    DateTimeField,
    FloatField,
    ForeignKeyField,
    IntegerField,
    TextField,
    UUIDField,
)
from playhouse.postgres_ext import JSONField

from app.models.base.base_model import BaseModel
from app.models.dataset.dataset_model import DatasetVersion
from app.models.project.project_model import ResearchProject


def utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


class AnalysisRun(BaseModel):
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    project = ForeignKeyField(ResearchProject, backref="analysis_runs", on_delete="CASCADE")
    status = CharField(max_length=50, default="queued")
    query = TextField()
    target_application = CharField(max_length=255)
    target_tissue = CharField(max_length=255)
    constraints = JSONField(null=True)
    started_at = DateTimeField(null=True)
    finished_at = DateTimeField(null=True)
    error_message = TextField(null=True)
    created_at = DateTimeField(default=utc_now)
    updated_at = DateTimeField(default=utc_now)

    def save(self, *args, **kwargs):
        self.updated_at = utc_now()  # pyrefly: ignore
        return super().save(*args, **kwargs)

    class Meta:  # pyrefly: ignore
        table_name = "analysis_run"


class AnalysisStep(BaseModel):
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    analysis_run = ForeignKeyField(AnalysisRun, backref="steps", on_delete="CASCADE")
    sequence_number = IntegerField(default=0)
    step_name = CharField(max_length=255)
    status = CharField(max_length=50, default="queued")
    input_snapshot = JSONField(null=True)
    output_snapshot = JSONField(null=True)
    started_at = DateTimeField(null=True)
    finished_at = DateTimeField(null=True)
    error_message = TextField(null=True)
    created_at = DateTimeField(default=utc_now)

    class Meta:  # pyrefly: ignore
        table_name = "analysis_step"


class CandidateMatch(BaseModel):
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    analysis_run = ForeignKeyField(AnalysisRun, backref="candidate_matches", on_delete="CASCADE")
    dataset_version = ForeignKeyField(
        DatasetVersion,
        backref="candidate_matches",
        null=True,
        on_delete="SET NULL",
    )
    rank = IntegerField()
    candidate_name = CharField(max_length=255)
    target_name = CharField(max_length=255)
    score = FloatField(null=True)
    method = CharField(max_length=255)
    features_used = IntegerField(null=True)
    metadata = JSONField(null=True)
    created_at = DateTimeField(default=utc_now)

    class Meta:  # pyrefly: ignore
        table_name = "candidate_match"
