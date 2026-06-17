import os
import threading
from typing import Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
import httpx
from app.models.base.base_model import db
from app.models.model.model_config_model import ModelConfig
from app.repositories.model_repository import ModelRepository


class ModelServiceError(Exception):
    def __init__(self, detail: Any):
        super().__init__(str(detail))
        self.detail = detail


class ModelCreatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=255)
    provider: str = Field(pattern=r"^(ollama|litellm)$")
    model_id: str = Field(min_length=1, max_length=255)
    api_key: str | None = None


class ModelRead(BaseModel):
    id: UUID
    name: str
    provider: str
    model_id: str
    is_active: bool
    status: str
    metadata_: dict[str, Any] | None
    created_at: Any


OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")


class ModelService:
    def __init__(self) -> None:
        self.repository = ModelRepository()

    def list_models(self) -> list[ModelRead]:
        return [self._to_read(m) for m in self.repository.list_all()]

    def add_model(self, payload: ModelCreatePayload) -> ModelRead:
        if payload.provider == "litellm" and not payload.api_key:
            raise ModelServiceError("API key required for LiteLLM models")
        status = "pulling" if payload.provider == "ollama" else "ready"
        model_id = payload.model_id
        if payload.provider == "ollama" and not model_id.startswith("ollama/"):
            model_id = f"ollama/{model_id}"
        model = self.repository.create(
            name=payload.name,
            provider=payload.provider,
            model_id=model_id,
            api_key_encrypted=payload.api_key,
            status=status,
        )
        if payload.provider == "ollama":
            threading.Thread(target=self._pull_and_update, args=(str(model.id), payload.model_id), daemon=True).start()
        return self._to_read(model)

    def _pull_and_update(self, model_id: str, tag: str) -> None:
        try:
            r = httpx.post(f"{OLLAMA_URL}/api/pull", json={"name": tag, "stream": False}, timeout=600)
            r.raise_for_status()
            db.connect(reuse_if_open=True)
            model = ModelConfig.get_by_id(model_id)
            model.status = "ready"
            model.save()
        except Exception:
            db.connect(reuse_if_open=True)
            model = ModelConfig.get_by_id(model_id)
            if model:
                model.status = "error"
                model.save()

    def delete_model(self, model_id: UUID) -> None:
        model = self.repository.get(model_id)
        if model is None:
            raise ModelServiceError(f"model {model_id} not found")
        if model.provider == "ollama":
            try:
                self._delete_ollama_model(model.model_id)
            except Exception:
                pass
        self.repository.delete(model)

    def list_ollama_models(self) -> list[dict]:
        try:
            r = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=10)
            r.raise_for_status()
            return r.json().get("models", [])
        except Exception as e:
            raise ModelServiceError(f"Ollama unreachable: {e}")

    def pull_ollama_model(self, model_name: str):
        try:
            r = httpx.post(f"{OLLAMA_URL}/api/pull", json={"name": model_name, "stream": False}, timeout=600)
            r.raise_for_status()
            return {"status": "ok"}
        except Exception as e:
            raise ModelServiceError(f"Ollama pull failed: {e}")

    def _delete_ollama_model(self, model_name: str):
        try:
            r = httpx.delete(f"{OLLAMA_URL}/api/delete", json={"name": model_name}, timeout=60)
            r.raise_for_status()
        except Exception as e:
            raise ModelServiceError(f"Ollama delete failed: {e}")

    def test_litellm_key(self, provider: str, model_id: str, api_key: str) -> dict:
        try:
            from litellm import completion
            response = completion(
                model=model_id,
                messages=[{"role": "user", "content": "hi"}],
                api_key=api_key,
                max_tokens=5,
            )
            return {"ok": True, "model": response.model}
        except Exception as e:
            raise ModelServiceError(f"Key validation failed: {e}")

    def _to_read(self, m: ModelConfig) -> ModelRead:
        return ModelRead(
            id=m.id,
            name=m.name,
            provider=m.provider,
            model_id=m.model_id,
            is_active=m.is_active,
            status=m.status,
            metadata_=m.metadata_,
            created_at=m.created_at,
        )
