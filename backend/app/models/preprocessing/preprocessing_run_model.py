import datetime
import uuid
from peewee import UUIDField, ForeignKeyField, CharField, TextField, DateTimeField
from playhouse.postgres_ext import JSONField
from app.models.base.base_model import BaseModel
from app.models.dataset.dataset_model import DatasetVersion

def utc_now():
    return datetime.datetime.now(datetime.timezone.utc)

class PreprocessingRun(BaseModel):
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    dataset_version = ForeignKeyField(DatasetVersion, backref='preprocessing_runs', on_delete='CASCADE')
    status = CharField(max_length=50)  # pending, running, completed, failed
    config = JSONField(null=True)
    log_path = TextField(null=True)
    error_message = TextField(null=True)
    started_at = DateTimeField(null=True)
    finished_at = DateTimeField(null=True)
    created_at = DateTimeField(default=utc_now)
    updated_at = DateTimeField(default=utc_now)

    def save(self, *args, **kwargs):
        self.updated_at = utc_now()  # pyrefly: ignore
        return super().save(*args, **kwargs)

    class Meta:  # pyrefly: ignore
        table_name = 'preprocessing_run'