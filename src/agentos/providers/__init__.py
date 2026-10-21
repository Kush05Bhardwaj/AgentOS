"""Provider-neutral chat interfaces for AgentOS."""

from agentos.providers.base import ChatProvider
from agentos.providers.errors import (
    AuthenticationError,
    InvalidProviderResponseError,
    ModelUnavailableError,
    ProviderError,
    ProviderTimeoutError,
    RateLimitError,
)
from agentos.providers.factory import create_provider
from agentos.providers.models import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    CompletionUsage,
    FinishReason,
    MessageRole,
)
from agentos.providers.selection import (
    ModelSelection,
    resolve_model_selection,
)

__all__ = [
    "AuthenticationError",
    "ChatMessage",
    "ChatProvider",
    "ChatRequest",
    "ChatResponse",
    "CompletionUsage",
    "FinishReason",
    "InvalidProviderResponseError",
    "MessageRole",
    "ModelSelection",
    "ModelUnavailableError",
    "ProviderError",
    "ProviderTimeoutError",
    "RateLimitError",
    "create_provider",
    "resolve_model_selection",
]
