from uuid import UUID, uuid4
from app.models.base.base_model import db
from app.models.model.model_config_model import ModelConfig


class ModelRepository:
    def create(self, **fields) -> ModelConfig:
        with db.atomic():
            return ModelConfig.create(id=uuid4(), **fields)

    def list_all(self) -> list[ModelConfig]:
        return list(ModelConfig.select().order_by(ModelConfig.created_at.desc()))

    def get(self, model_id: UUID) -> ModelConfig | None:
        return ModelConfig.get_or_none(ModelConfig.id == model_id)

    def delete(self, model: ModelConfig) -> int:
        with db.atomic():
            return model.delete_instance()
