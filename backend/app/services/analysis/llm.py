"""Build the chat model for the reasoning agent from the configured provider."""

import os

DEFAULT_MODEL = "ollama/qwen2.5:7b"


def build_chat_model(model: str | None = None):
    """Construct a ChatLiteLLM from a model string.

    model format: "ollama/qwen2.5:7b" or "openai/gpt-4o" or "anthropic/claude-3-haiku-20240307"
    Falls back to MATCHMAKER_LLM env var, then DEFAULT_MODEL.
    """
    from langchain_community.chat_models import ChatLiteLLM

    model_name = model or os.getenv("MATCHMAKER_LLM", DEFAULT_MODEL)
    kwargs: dict = {"model": model_name, "temperature": 0}

    if model_name.startswith("ollama/"):
        base_url = os.getenv("OLLAMA_BASE_URL")
        if base_url:
            kwargs["api_base"] = base_url

    return ChatLiteLLM(**kwargs)
