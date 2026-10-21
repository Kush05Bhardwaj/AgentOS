"""OpenAI-compatible chat completion adapter."""

from __future__ import annotations

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

_DEFAULT_BASE_URL = "https://api.openai.com/v1"


def _normalize_finish_reason(value: str) -> FinishReason:
    """Normalize a provider's completion reason."""
    try:
        return FinishReason(value)
    except ValueError:
        return FinishReason.UNKNOWN


def _read_token_count(
    usage: Mapping[str, object],
    name: str,
) -> int:
    """Read a non-negative integer usage field."""
    value = usage.get(name, 0)

    if type(value) is not int or value < 0:
        raise InvalidProviderResponseError(f"Provider returned an invalid '{name}' token count.")

    return value


class OpenAICompatibleProvider(ChatProvider):
    """Call an OpenAI-compatible chat completions endpoint."""

    def __init__(
        self,
        base_url: str = _DEFAULT_BASE_URL,
        *,
        api_key: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialize the adapter with an endpoint and optional credential."""
        if not isinstance(base_url, str) or not base_url.strip():
            raise ValueError("base_url must be a non-empty URL.")

        if base_url != base_url.strip():
            raise ValueError("base_url must not contain surrounding whitespace.")

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
                "base_url must be an absolute HTTP(S) URL without "
                "embedded credentials, a query, or a fragment."
            )

        try:
            _ = parsed.port
        except ValueError as exc:
            raise ValueError("base_url contains an invalid port.") from exc

        if api_key is not None:
            if not isinstance(api_key, str) or not api_key.strip():
                raise ValueError("api_key must be a non-empty string when provided.")
            api_key = api_key.strip()

        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient()

    async def aclose(self) -> None:
        """Close the HTTP client when owned by this provider."""
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> OpenAICompatibleProvider:
        """Support asynchronous context-manager usage."""
        return self

    async def __aexit__(
        self,
        exc_type: object,
        exc: object,
        traceback: object,
    ) -> None:
        """Release resources owned by this provider."""
        await self.aclose()

    async def complete(self, request: ChatRequest) -> ChatResponse:
        """Request one completion and normalize the response."""
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

        headers: dict[str, str] = {}

        if self._api_key is not None:
            headers["Authorization"] = f"Bearer {self._api_key}"

        try:
            response = await self._client.post(
                f"{self._base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=request.request_timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(
                "Chat completion request exceeded the configured "
                f"timeout of {request.request_timeout_seconds} seconds."
            ) from exc
        except httpx.RequestError as exc:
            raise ProviderError(
                f"Could not connect to the configured provider at {self._base_url}."
            ) from exc

        self._raise_for_status(response)

        try:
            data = response.json()
        except ValueError as exc:
            raise InvalidProviderResponseError("Provider returned invalid JSON.") from exc

        if not isinstance(data, Mapping):
            raise InvalidProviderResponseError("Provider response must be a JSON object.")

        choices = data.get("choices")

        if not isinstance(choices, list) or not choices:
            raise InvalidProviderResponseError("Provider response has no completion choices.")

        choice = choices[0]

        if not isinstance(choice, Mapping):
            raise InvalidProviderResponseError("Provider completion choice must be an object.")

        message = choice.get("message")

        if not isinstance(message, Mapping):
            raise InvalidProviderResponseError("Provider completion is missing its message object.")

        text = message.get("content")

        if not isinstance(text, str):
            raise InvalidProviderResponseError(
                "Provider completion message must contain text content."
            )

        model = data.get("model", request.model)

        if not isinstance(model, str) or not model.strip():
            raise InvalidProviderResponseError("Provider response contains an invalid model name.")

        reason = choice.get("finish_reason", "unknown")

        if not isinstance(reason, str):
            raise InvalidProviderResponseError(
                "Provider response contains an invalid finish reason."
            )

        usage_data = data.get("usage")
        usage: CompletionUsage | None = None

        if usage_data is not None:
            if not isinstance(usage_data, Mapping):
                raise InvalidProviderResponseError("Provider usage data must be a JSON object.")

            prompt_tokens = _read_token_count(
                usage_data,
                "prompt_tokens",
            )
            completion_tokens = _read_token_count(
                usage_data,
                "completion_tokens",
            )
            total_tokens = _read_token_count(
                usage_data,
                "total_tokens",
            )

            # Compatible providers may omit total_tokens.
            if "total_tokens" not in usage_data:
                total_tokens = prompt_tokens + completion_tokens

            usage = CompletionUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            )

        return ChatResponse(
            text=text,
            model=model.strip(),
            finish_reason=_normalize_finish_reason(reason),
            usage=usage,
        )

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        """Translate HTTP failures into provider-neutral exceptions."""
        status = response.status_code

        if status in {401, 403}:
            raise AuthenticationError(f"Provider rejected authentication (HTTP {status}).")

        if status == 404:
            raise ModelUnavailableError("Provider could not find the requested model or endpoint.")

        if status == 429:
            raise RateLimitError("Provider rate-limited the request.")

        if status in {408, 504}:
            raise ProviderTimeoutError(f"Provider request timed out (HTTP {status}).")

        if status >= 400:
            raise ProviderError(f"Provider chat request failed with HTTP {status}.")
