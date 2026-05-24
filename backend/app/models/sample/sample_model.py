import datetime
import uuid
from peewee import UUIDField, CharField, TextField, FloatField, ForeignKeyField, DateTimeField
from playhouse.postgres_ext import JSONField
from app.models.base.base_model import BaseModel
from app.models.dataset.dataset_model import DatasetVersion

def utc_now():
    return datetime.datetime.now(datetime.timezone.utc)

class Sample(BaseModel):
    """Biological sample (tissue region, cell type, or experimental condition)"""
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    dataset_version = ForeignKeyField(DatasetVersion, backref='samples', on_delete='CASCADE')
    name = CharField(max_length=255)  # "Amnion_decell_1"
    type = CharField(max_length=50)   # 'placenta_region', 'heart_region', 'cell_type'
    metadata = JSONField(null=True)   # {"decellularized": true, "biological_replicate": 1}
    created_at = DateTimeField(default=utc_now)

    class Meta:  # pyrefly: ignore
        table_name = 'sample'

class Measurement(BaseModel):
    """Feature (protein/gene) expression measurement for a sample"""
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    sample = ForeignKeyField(Sample, backref='measurements', on_delete='CASCADE')
    feature_name = CharField(max_length=255)  # GeneName or UniProt ID
    raw_value = FloatField()  # original intensity/value
    normalized_value = FloatField(null=True)  # after preprocessing
    unit = CharField(max_length=50, null=True)  # "log2 intensity"
    created_at = DateTimeField(default=utc_now)

    class Meta:  # pyrefly: ignore
        table_name = 'measurement'