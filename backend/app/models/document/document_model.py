import datetime
import uuid

from peewee import CharField, DateTimeField, ForeignKeyField, IntegerField, TextField, UUIDField
from playhouse.postgres_ext import JSONField

from app.models.base.base_model import BaseModel
from app.models.project.project_model import ResearchProject


def utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


class Document(BaseModel):
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    project = ForeignKeyField(ResearchProject, backref="documents", on_delete="CASCADE")
    title = CharField(max_length=255)
    original_filename = CharField(max_length=255)
    storage_path = TextField()
    status = CharField(max_length=50, default="registered")
    metadata = JSONField(null=True)
    created_at = DateTimeField(default=utc_now)
    updated_at = DateTimeField(default=utc_now)

    def save(self, *args, **kwargs):
        self.updated_at = utc_now()  # pyrefly: ignore
        return super().save(*args, **kwargs)

    class Meta:  # pyrefly: ignore
        table_name = "document"


class DocumentChunk(BaseModel):
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    document = ForeignKeyField(Document, backref="chunks", on_delete="CASCADE")
    chunk_index = IntegerField()
    page_number = IntegerField(null=True)
    text = TextField()
    vector_id = CharField(max_length=255, null=True)
    metadata = JSONField(null=True)
    created_at = DateTimeField(default=utc_now)

    class Meta:  # pyrefly: ignore
        table_name = "document_chunk"
