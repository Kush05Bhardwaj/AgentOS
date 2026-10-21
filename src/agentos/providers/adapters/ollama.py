"""Ollama chat completion adapter."""

from collections.abc import Mapping
from urllib.parse import urlsplit

import httpx

from agentos.providers.base import ChatProvider
from agentos.providers.errors import (
    AuthenticationError,
    InvalidProviderResponseError,
    ModelUnavailableError,
    ProviderError,
    ProviderTimeoutError,
    RateLimitError,
)
from agentos.providers.models import (
    ChatRequest,
    ChatResponse,
    CompletionUsage,
    FinishReason,
)

_DEFAULT_BASE_URL = "http://localhost:11434"


def _normalize_finish_reason(value: str) -> FinishReason:
    """Map Ollama completion reasons to AgentOS finish reasons."""
    mapping = {
        "stop": FinishReason.STOP,
        "length": FinishReason.LENGTH,
        "content_filter": FinishReason.CONTENT_FILTER,
    }
    return mapping.get(value, FinishReason.UNKNOWN)


def _read_token_count(payload: Mapping[str, object], key: str) -> int:
    """Read a non-negative integer token count from an Ollama response."""
    value = payload.get(key, 0)

    if type(value) is not int or value < 0:
        raise InvalidProviderResponseError(f"Ollama returned an invalid '{key}' token count.")

    return value


class OllamaProvider(ChatProvider):
    """Call Ollama's non-streaming chat API."""

    def __init__(
        self,
        base_url: str = _DEFAULT_BASE_URL,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        """Create an adapter, optionally with an injected HTTP client."""
        if not isinstance(base_url, str) or not base_url.strip():
            raise ValueError("Ollama base_url must be a non-empty URL.")

        if base_url != base_url.strip():
            raise ValueError("Ollama base_url must not contain surrounding whitespace.")

        parsed = urlsplit(base_url)

        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError(
                "Ollama base_url must be an absolute HTTP(S) URL "
                "without embedded credentials, a query, or a fragment."
            )

        try:
            _ = parsed.port
        except ValueError as exc:
            raise ValueError("Ollama base_url contains an invalid port.") from exc

        self._base_url = base_url.rstrip("/")
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient()

    async def aclose(self) -> None:
        """Close the HTTP client if this provider created it."""
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "OllamaProvider":
        """Allow provider lifecycle management with async with."""
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        """Release resources owned by this provider."""
        await self.aclose()

    async def complete(self, request: ChatRequest) -> ChatResponse:
        """Generate one chat completion and normalize its response."""
        payload = {
            "model": request.model,
            "messages": [
                {
                    "role": message.role.value,
                    "content": message.content,
                }
                for message in request.messages
            ],
            "stream": False,
        }

        try:
            response = await self._client.post(
                f"{self._base_url}/api/chat",
                json=payload,
                timeout=request.request_timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(
                "Ollama request exceeded the configured timeout "
                f"of {request.request_timeout_seconds} seconds."
            ) from exc
        except httpx.RequestError as exc:
            raise ProviderError(f"Could not connect to Ollama at {self._base_url}.") from exc

        self._raise_for_status(response)

        try:
            data = response.json()
        except ValueError as exc:
            raise InvalidProviderResponseError("Ollama returned invalid JSON.") from exc

        if not isinstance(data, Mapping):
            raise InvalidProviderResponseError("Ollama response must be a JSON object.")

        message = data.get("message")
        if not isinstance(message, Mapping):
            raise InvalidProviderResponseError("Ollama response is missing its message object.")

        text = message.get("content")
        if not isinstance(text, str):
            raise InvalidProviderResponseError("Ollama response message is missing text content.")

        returned_model = data.get("model", request.model)
        if not isinstance(returned_model, str) or not returned_model.strip():
            raise InvalidProviderResponseError("Ollama response contains an invalid model name.")

        done = data.get("done")
        if done is not None and not isinstance(done, bool):
            raise InvalidProviderResponseError("Ollama response has an invalid completion status.")

        if done is False:
            raise InvalidProviderResponseError(
                "Ollama returned an incomplete non-streaming response."
            )

        reason = data.get("done_reason", "unknown")
        if not isinstance(reason, str):
            raise InvalidProviderResponseError(
                "Ollama response contains an invalid completion reason."
            )

        usage: CompletionUsage | None = None

        if "prompt_eval_count" in data or "eval_count" in data:
            prompt_tokens = _read_token_count(data, "prompt_eval_count")
            completion_tokens = _read_token_count(data, "eval_count")

            usage = CompletionUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            )

        return ChatResponse(
            text=text,
            model=returned_model.strip(),
            finish_reason=_normalize_finish_reason(reason),
            usage=usage,
        )

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        """Translate HTTP failures into provider-neutral exceptions."""
        status = response.status_code

        if status in {401, 403}:
            raise AuthenticationError(f"Ollama endpoint rejected authentication (HTTP {status}).")

        if status == 404:
            raise ModelUnavailableError(
                "Ollama could not find the requested model or chat endpoint."
            )

        if status == 429:
            raise RateLimitError("Ollama rate-limited the request.")

        if status >= 400:
            raise ProviderError(f"Ollama chat request failed with HTTP {status}.")
