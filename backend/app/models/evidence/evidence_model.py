import datetime
import uuid

from peewee import CharField, DateTimeField, FloatField, ForeignKeyField, TextField, UUIDField
from playhouse.postgres_ext import JSONField

from app.models.base.base_model import BaseModel
from app.models.document.document_model import Document, DocumentChunk
from app.models.run.run_model import AnalysisRun, CandidateMatch


def utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


class EvidenceItem(BaseModel):
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    analysis_run = ForeignKeyField(AnalysisRun, backref="evidence_items", on_delete="CASCADE")
    candidate_match = ForeignKeyField(
        CandidateMatch,
        backref="evidence_items",
        null=True,
        on_delete="SET NULL",
    )
    candidate_name = CharField(max_length=255)
    claim = TextField()
    document = ForeignKeyField(Document, backref="evidence_items", null=True, on_delete="SET NULL")
    document_chunk = ForeignKeyField(
        DocumentChunk,
        backref="evidence_items",
        null=True,
        on_delete="SET NULL",
    )
    support_label = CharField(max_length=50, default="supporting")
    score = FloatField(null=True)
    metadata = JSONField(null=True)
    created_at = DateTimeField(default=utc_now)

    class Meta:  # pyrefly: ignore
        table_name = "evidence_item"


class ContradictionWarning(BaseModel):
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    analysis_run = ForeignKeyField(AnalysisRun, backref="warnings", on_delete="CASCADE")
    candidate_match = ForeignKeyField(
        CandidateMatch,
        backref="warnings",
        null=True,
        on_delete="SET NULL",
    )
    candidate_name = CharField(max_length=255, null=True)
    warning_type = CharField(max_length=100)
    severity = CharField(max_length=50, default="warning")
    message = TextField()
    metadata = JSONField(null=True)
    created_at = DateTimeField(default=utc_now)

    class Meta:  # pyrefly: ignore
        table_name = "contradiction_warning"
