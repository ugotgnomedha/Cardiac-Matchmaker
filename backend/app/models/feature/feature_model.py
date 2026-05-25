"""Per-protein annotation (matrisome class, UniProt id, heart presence) for a dataset version."""

import datetime
import uuid

from peewee import BooleanField, CharField, DateTimeField, ForeignKeyField, UUIDField

from app.models.base.base_model import BaseModel
from app.models.dataset.dataset_model import DatasetVersion


def utc_now() -> datetime.datetime:
    """Current UTC time."""
    return datetime.datetime.now(datetime.timezone.utc)


class FeatureAnnotation(BaseModel):
    """Descriptive columns the matcher needs, one row per feature (GeneName) per dataset version."""

    id = UUIDField(primary_key=True, default=uuid.uuid4)
    dataset_version = ForeignKeyField(
        DatasetVersion, backref="feature_annotations", on_delete="CASCADE"
    )
    feature_name = CharField(max_length=255)
    uniprot = CharField(max_length=64, null=True)
    matrisome_division = CharField(max_length=128, null=True)
    matrisome_category = CharField(max_length=128, null=True)
    location = CharField(max_length=255, null=True)
    present_in_heart = BooleanField(default=False)
    created_at = DateTimeField(default=utc_now)

    class Meta:  # pyrefly: ignore
        table_name = "feature_annotation"
