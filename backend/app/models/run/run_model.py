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


class CardiacApplicationQuery(BaseModel):
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    project = ForeignKeyField(ResearchProject, backref="cardiac_application_queries", on_delete="CASCADE")
    query_text = TextField()
    target_application = CharField(max_length=255)
    target_tissue = CharField(max_length=255)
    function_target = CharField(max_length=255, null=True)
    constraints = JSONField(null=True)
    created_at = DateTimeField(default=utc_now)
    updated_at = DateTimeField(default=utc_now)

    def save(self, *args, **kwargs):
        self.updated_at = utc_now()  # pyrefly: ignore
        return super().save(*args, **kwargs)

    class Meta:  # pyrefly: ignore
        table_name = "cardiac_application_query"


class AnalysisRun(BaseModel):
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    project = ForeignKeyField(ResearchProject, backref="analysis_runs", on_delete="CASCADE")
    application_query = ForeignKeyField(
        CardiacApplicationQuery,
        backref="analysis_runs",
        on_delete="CASCADE",
    )
    status = CharField(max_length=50, default="queued")
    selected_config = JSONField(null=True)
    started_at = DateTimeField(null=True)
    finished_at = DateTimeField(null=True)
    error_message = TextField(null=True)
    created_at = DateTimeField(default=utc_now)
    updated_at = DateTimeField(default=utc_now)

    def save(self, *args, **kwargs):
        self.updated_at = utc_now()  # pyrefly: ignore
        return super().save(*args, **kwargs)

    @classmethod
    def create(cls, **query):
        query_text = query.pop("query", None)
        target_application = query.pop("target_application", None)
        target_tissue = query.pop("target_tissue", None)
        function_target = query.pop("function_target", None)
        constraints = query.pop("constraints", None)

        if "application_query" not in query and query_text is not None:
            project = query.get("project")
            if project is None:
                raise ValueError("project is required when creating an AnalysisRun from query fields")
            query["application_query"] = CardiacApplicationQuery.create(
                project=project,
                query_text=query_text,
                target_application=target_application or "",
                target_tissue=target_tissue or "",
                function_target=function_target,
                constraints=constraints,
            )

        return super().create(**query)

    @property
    def query(self) -> str:
        return self.application_query.query_text

    @property
    def target_application(self) -> str:
        return self.application_query.target_application

    @property
    def target_tissue(self) -> str:
        return self.application_query.target_tissue

    @property
    def function_target(self) -> str | None:
        return self.application_query.function_target

    @property
    def constraints(self) -> dict | None:
        return self.application_query.constraints

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
