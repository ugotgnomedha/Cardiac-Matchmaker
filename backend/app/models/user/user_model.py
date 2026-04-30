import datetime
from peewee import UUIDField, CharField, BooleanField, DateTimeField

from app.models.base.base_model import BaseModel


def utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)

class User(BaseModel):
    id = UUIDField(primary_key=True)
    email = CharField(unique=True)
    password_hash = CharField()
    is_active = BooleanField(default=True)
    is_superuser = BooleanField(default=False)
    created_at = DateTimeField(default=utc_now)
    updated_at = DateTimeField(default=utc_now)

    def save(self, *args, **kwargs):
        setattr(self, "updated_at", utc_now())
        return super().save(*args, **kwargs)