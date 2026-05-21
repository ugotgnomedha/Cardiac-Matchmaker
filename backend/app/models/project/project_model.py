import datetime
import uuid

from peewee import UUIDField, CharField, TextField, DateTimeField

from app.models.base.base_model import BaseModel

def utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)

class ResearchProject(BaseModel):
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    name = CharField(max_length=255)
    description = TextField(null=True)
    created_at = DateTimeField(default=utc_now)
    updated_at = DateTimeField(default=utc_now)

    def save(self, *args, **kwargs):
        self.updated_at = utc_now()  # pyrefly: ignore
        return super().save(*args, **kwargs)

    class Meta:  # pyrefly: ignore
        table_name = "research_project"