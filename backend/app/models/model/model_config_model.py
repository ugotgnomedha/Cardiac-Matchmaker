import datetime
import uuid
from peewee import UUIDField, CharField, TextField, BooleanField, DateTimeField
from playhouse.postgres_ext import JSONField
from app.models.base.base_model import BaseModel


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc)


class ModelConfig(BaseModel):
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    name = CharField(max_length=255)
    provider = CharField(max_length=20)
    model_id = CharField(max_length=255)
    api_key_encrypted = TextField(null=True)
    is_active = BooleanField(default=True)
    metadata_ = JSONField(null=True)
    created_at = DateTimeField(default=utc_now)
    updated_at = DateTimeField(default=utc_now)

    def save(self, *args, **kwargs):
        self.updated_at = utc_now()
        return super().save(*args, **kwargs)

    class Meta:
        table_name = "model_config"
