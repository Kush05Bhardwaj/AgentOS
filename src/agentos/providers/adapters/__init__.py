"""Concrete AI provider adapters."""

from agentos.providers.adapters.ollama import OllamaProvider
from agentos.providers.adapters.openai_compatible import OpenAICompatibleProvider

__all__ = [
    "OllamaProvider",
    "OpenAICompatibleProvider",
]
