"""Build the chat model for the reasoning agent from the configured provider."""

import os

DEFAULT_MODEL = "ollama/qwen2.5:7b"


def _lookup_api_key(model_id: str) -> str | None:
    """Look up the API key for a model from the ModelConfig table."""
    try:
        from app.models.base.base_model import db
        from app.models.model.model_config_model import ModelConfig

        db.connect(reuse_if_open=True)
        row = ModelConfig.get_or_none(ModelConfig.model_id == model_id)
        return row.api_key if row else None
    except Exception:
        return None


def build_chat_model(model: str | None = None):
    """Construct a ChatLiteLLM from a model string.

    model format: "ollama/qwen2.5:7b" or "openai/gpt-4o" or "deepseek/deepseek-chat"
    Falls back to MATCHMAKER_LLM env var, then DEFAULT_MODEL.
    For non-Ollama models, looks up the API key from the ModelConfig table.
    """
    from langchain_community.chat_models import ChatLiteLLM

    model_name = model or os.getenv("MATCHMAKER_LLM", DEFAULT_MODEL)

    # Backward compat: unqualified tags (qwen2.5:7b) default to ollama
    if "/" not in model_name:
        model_name = f"ollama/{model_name}"

    kwargs: dict = {"model": model_name, "temperature": 0}

    if model_name.startswith("ollama/"):
        base_url = os.getenv("OLLAMA_BASE_URL")
        if base_url:
            kwargs["api_base"] = base_url
    else:
        api_key = _lookup_api_key(model_name)
        if api_key:
            kwargs["api_key"] = api_key

    return ChatLiteLLM(**kwargs)
