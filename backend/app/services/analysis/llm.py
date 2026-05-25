"""Build the local Ollama chat model used by the reasoning agent."""

import os

DEFAULT_MODEL = "qwen2.5:7b"


def build_chat_model(model: str | None = None):
    """Construct a ChatOllama from env (MATCHMAKER_LLM model, OLLAMA_BASE_URL)."""
    from langchain_ollama import ChatOllama  # pyrefly: ignore

    kwargs: dict = {"model": model or os.getenv("MATCHMAKER_LLM", DEFAULT_MODEL), "temperature": 0}
    base_url = os.getenv("OLLAMA_BASE_URL")
    if base_url:
        kwargs["base_url"] = base_url
    return ChatOllama(**kwargs)
