import datetime
import uuid
from peewee import UUIDField, CharField, TextField, ForeignKeyField, DateTimeField
from playhouse.postgres_ext import JSONField
from app.models.base.base_model import BaseModel
from app.models.project.project_model import ResearchProject

def utc_now():
    return datetime.datetime.now(datetime.timezone.utc)

class Dataset(BaseModel):
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    project = ForeignKeyField(ResearchProject, backref='datasets', on_delete='CASCADE')
    name = CharField(max_length=255)
    type = CharField(max_length=50)  # 'placenta', 'cardiac', 'placenta_heart_merged'
    original_filename = CharField(max_length=255)
    storage_path = TextField()
    metadata = JSONField(null=True)
    created_at = DateTimeField(default=utc_now)
    updated_at = DateTimeField(default=utc_now)

    def save(self, *args, **kwargs):
        self.updated_at = utc_now()  # pyrefly: ignore
        return super().save(*args, **kwargs)

    class Meta:  # pyrefly: ignore
        table_name = 'dataset'

class DatasetVersion(BaseModel):
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    dataset = ForeignKeyField(Dataset, backref='versions', on_delete='CASCADE')
    version_number = CharField(max_length=20)
    status = CharField(max_length=50)  # raw, validated, normalized, failed
    storage_path = TextField()
    preprocessing_config = JSONField(null=True)
    created_at = DateTimeField(default=utc_now)

    class Meta:  # pyrefly: ignore
        table_name = 'dataset_version'