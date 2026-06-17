from typing import NoReturn
from uuid import UUID
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
import httpx
import json
from app.services.model.model_service import (
    ModelCreatePayload, ModelRead, ModelService, ModelServiceError,
    OLLAMA_URL,
)

model_router = APIRouter(prefix="/models", tags=["models"])
model_service = ModelService()


def _raise_http(exc: Exception) -> NoReturn:
    if isinstance(exc, ModelServiceError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc.detail)) from exc
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="unexpected error") from exc


@model_router.get("", response_model=list[ModelRead])
def list_models():
    return model_service.list_models()


@model_router.post("", response_model=ModelRead, status_code=status.HTTP_201_CREATED)
def add_model(payload: ModelCreatePayload):
    try:
        return model_service.add_model(payload)
    except ModelServiceError as exc:
        _raise_http(exc)


@model_router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_model(model_id: UUID):
    try:
        model_service.delete_model(model_id)
    except ModelServiceError as exc:
        _raise_http(exc)


@model_router.get("/ollama/list")
def list_ollama_models():
    try:
        return model_service.list_ollama_models()
    except ModelServiceError as exc:
        _raise_http(exc)


@model_router.post("/ollama/pull")
def pull_ollama_model(payload: dict):
    try:
        return model_service.pull_ollama_model(payload["name"])
    except ModelServiceError as exc:
        _raise_http(exc)


@model_router.post("/ollama/pull/stream")
async def pull_ollama_model_stream(payload: dict):
    name = payload.get("name", "")
    if not name:
        raise HTTPException(status_code=422, detail="name is required")

    async def event_stream():
        async with httpx.AsyncClient(timeout=600) as client:
            try:
                async with client.stream("POST", f"{OLLAMA_URL}/api/pull", json={"name": name, "stream": True}) as r:
                    r.raise_for_status()
                    async for line in r.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            data = json.loads(line)
                            yield f"data: {json.dumps(data)}\n\n"
                            if data.get("status") == "success":
                                break
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@model_router.post("/test-key")
def test_api_key(payload: dict):
    try:
        return model_service.test_litellm_key(
            payload["provider"], payload["model_id"], payload["api_key"]
        )
    except ModelServiceError as exc:
        _raise_http(exc)
