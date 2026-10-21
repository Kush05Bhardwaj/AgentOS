"""Provider-neutral chat request and response types."""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from agentos.config.defaults import (
    DEFAULT_REQUEST_TIMEOUT_SECONDS,
    REQUEST_TIMEOUT_MAXIMUM,
    REQUEST_TIMEOUT_MINIMUM,
)


class MessageRole(StrEnum):
    """Roles that may author a chat message."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class FinishReason(StrEnum):
    """Normalized completion status reported by a provider.

    Adapters map vendor-specific values onto one of these members and
    use UNKNOWN when no standard status applies.
    """

    STOP = "stop"
    LENGTH = "length"
    CONTENT_FILTER = "content_filter"
    UNKNOWN = "unknown"


def _require_text(name: str, value: object) -> str:
    """Return value as a stripped string, rejecting blank input."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string.")
    return value.strip()


@dataclass(frozen=True, slots=True)
class ChatMessage:
    """A single role-attributed message in a conversation."""

    role: MessageRole | str
    content: str

    def __post_init__(self) -> None:
        """Normalize the role and require non-blank content."""
        try:
            role = MessageRole(self.role)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Unsupported message role: {self.role!r}.") from exc

        if not isinstance(self.content, str) or not self.content.strip():
            raise ValueError("Chat message content must be a non-empty string.")

        object.__setattr__(self, "role", role)


@dataclass(frozen=True, slots=True)
class ChatRequest:
    """A provider-neutral request for a chat completion."""

    model: str
    messages: Sequence[ChatMessage]
    request_timeout_seconds: int = DEFAULT_REQUEST_TIMEOUT_SECONDS

    def __post_init__(self) -> None:
        """Normalize the model and messages, then validate the timeout."""
        object.__setattr__(self, "model", _require_text("model", self.model))

        try:
            messages = tuple(self.messages)
        except TypeError as exc:
            raise ValueError(
                "ChatRequest.messages must be a sequence of ChatMessage values."
            ) from exc

        if not messages:
            raise ValueError("ChatRequest.messages must contain at least one message.")

        if not all(isinstance(message, ChatMessage) for message in messages):
            raise ValueError("ChatRequest.messages must contain only ChatMessage values.")

        object.__setattr__(self, "messages", messages)

        if type(self.request_timeout_seconds) is not int or not (
            REQUEST_TIMEOUT_MINIMUM <= self.request_timeout_seconds <= REQUEST_TIMEOUT_MAXIMUM
        ):
            raise ValueError(
                "request_timeout_seconds must be between "
                f"{REQUEST_TIMEOUT_MINIMUM} and {REQUEST_TIMEOUT_MAXIMUM}."
            )


@dataclass(frozen=True, slots=True)
class CompletionUsage:
    """Token accounting reported by a provider, when available."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def __post_init__(self) -> None:
        """Require non-negative integer token counts."""
        for value in (self.prompt_tokens, self.completion_tokens, self.total_tokens):
            if type(value) is not int or value < 0:
                raise ValueError("Token counts must be non-negative integers.")


@dataclass(frozen=True, slots=True)
class ChatResponse:
    """A normalized completion produced by any provider.

    The text may be empty when a provider filters or truncates output,
    but the model must always identify what produced the response.
    """

    text: str
    model: str
    finish_reason: FinishReason | str = FinishReason.UNKNOWN
    usage: CompletionUsage | None = None

    def __post_init__(self) -> None:
        """Normalize the finish reason and validate response fields."""
        if not isinstance(self.text, str):
            raise ValueError("ChatResponse.text must be a string.")

        object.__setattr__(self, "model", _require_text("model", self.model))

        try:
            finish_reason = FinishReason(self.finish_reason)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Unsupported finish reason: {self.finish_reason!r}.") from exc

        object.__setattr__(self, "finish_reason", finish_reason)

        if self.usage is not None and not isinstance(self.usage, CompletionUsage):
            raise ValueError("ChatResponse.usage must be a CompletionUsage instance.")
