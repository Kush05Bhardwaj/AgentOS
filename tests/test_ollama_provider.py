"""Offline tests for the Ollama provider adapter."""

import asyncio
import json
from collections.abc import Callable

import httpx
import pytest

from agentos.providers.adapters import OllamaProvider
from agentos.providers.errors import (
    AuthenticationError,
    InvalidProviderResponseError,
    ModelUnavailableError,
    ProviderError,
    ProviderTimeoutError,
    RateLimitError,
)
from agentos.providers.models import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    CompletionUsage,
    FinishReason,
    MessageRole,
)

ResponseHandler = Callable[[httpx.Request], httpx.Response]


def _sample_request() -> ChatRequest:
    """Construct a representative request without model dependencies."""
    return ChatRequest(
        model="test-model",
        messages=(
            ChatMessage(role="system", content="Be helpful."),
            ChatMessage(role="user", content="Explain Python."),
        ),
        request_timeout_seconds=30,
    )


def _complete(
    handler: ResponseHandler,
    request: ChatRequest | None = None,
) -> ChatResponse:
    """Run a provider call against an in-memory HTTP transport."""

    async def execute() -> ChatResponse:
        transport = httpx.MockTransport(handler)

        async with httpx.AsyncClient(transport=transport) as client:
            provider = OllamaProvider(client=client)
            return await provider.complete(request or _sample_request())

    return asyncio.run(execute())


def _success_response(
    request: httpx.Request,
) -> httpx.Response:
    return httpx.Response(
        200,
        request=request,
        json={
            "model": "test-model",
            "message": {
                "role": "assistant",
                "content": "Python is a programming language.",
            },
            "done": True,
            "done_reason": "stop",
            "prompt_eval_count": 10,
            "eval_count": 7,
        },
    )


def test_successful_completion_is_normalized() -> None:
    response = _complete(_success_response)

    assert response.text == "Python is a programming language."
    assert response.model == "test-model"
    assert response.finish_reason == FinishReason.STOP
    assert response.usage == CompletionUsage(
        prompt_tokens=10,
        completion_tokens=7,
        total_tokens=17,
    )


def test_request_uses_ollama_chat_endpoint_and_non_streaming_mode() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["payload"] = json.loads(request.content)
        return _success_response(request)

    _complete(handler)

    assert captured["url"] == "http://localhost:11434/api/chat"

    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["model"] == "test-model"
    assert payload["stream"] is False
    assert payload["messages"] == [
        {"role": "system", "content": "Be helpful."},
        {"role": "user", "content": "Explain Python."},
    ]


def test_custom_base_url_is_used() -> None:
    async def execute() -> None:
        captured: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(str(request.url))
            return _success_response(request)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OllamaProvider(
                base_url="http://localhost:11434/",
                client=client,
            )
            await provider.complete(_sample_request())

        assert captured == ["http://localhost:11434/api/chat"]

    asyncio.run(execute())


def test_missing_optional_usage_is_allowed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            request=request,
            json={
                "message": {"content": "Hello"},
                "done": True,
            },
        )

    response = _complete(handler)

    assert response.text == "Hello"
    assert response.model == "test-model"
    assert response.finish_reason == FinishReason.UNKNOWN
    assert response.usage is None


@pytest.mark.parametrize(
    ("reason", "expected"),
    [
        ("stop", FinishReason.STOP),
        ("length", FinishReason.LENGTH),
        ("content_filter", FinishReason.CONTENT_FILTER),
        ("some_future_reason", FinishReason.UNKNOWN),
    ],
)
def test_finish_reason_mapping(
    reason: str,
    expected: FinishReason,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            request=request,
            json={
                "model": "test-model",
                "message": {"content": "Hello"},
                "done": True,
                "done_reason": reason,
            },
        )

    assert _complete(handler).finish_reason == expected


@pytest.mark.parametrize(
    ("status", "error_type"),
    [
        (401, AuthenticationError),
        (403, AuthenticationError),
        (404, ModelUnavailableError),
        (429, RateLimitError),
        (400, ProviderError),
        (500, ProviderError),
        (502, ProviderError),
    ],
)
def test_http_errors_are_normalized(
    status: int,
    error_type: type[ProviderError],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status,
            request=request,
            json={"error": "simulated failure"},
        )

    with pytest.raises(error_type):
        _complete(handler)


def test_timeout_is_normalized() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("simulated timeout", request=request)

    with pytest.raises(ProviderTimeoutError, match="30 seconds"):
        _complete(handler)


def test_connection_error_is_normalized() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("simulated connection failure", request=request)

    with pytest.raises(ProviderError, match="Could not connect to Ollama"):
        _complete(handler)


@pytest.mark.parametrize(
    "body",
    [
        b"not-json",
        b"null",
        b"[]",
        b'{"done": true}',
        b'{"message": {"content": 123}}',
        b'{"model": 123, "message": {"content": "Hello"}}',
        b'{"message": {"content": "Hello"}, "done": "yes"}',
        b'{"message": {"content": "Hello"}, "done": false}',
        b'{"message": {"content": "Hello"}, "done_reason": 123}',
        b'{"message": {"content": "Hello"}, "eval_count": -1}',
        b'{"message": {"content": "Hello"}, "prompt_eval_count": true}',
    ],
)
def test_malformed_responses_are_rejected(body: bytes) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            request=request,
            content=body,
            headers={"content-type": "application/json"},
        )

    with pytest.raises(InvalidProviderResponseError):
        _complete(handler)


@pytest.mark.parametrize(
    "base_url",
    [
        "",
        "not-a-url",
        "ftp://localhost:11434",
        "http://",
        "http://user:password@localhost:11434",
        "http://localhost:99999",
    ],
)
def test_invalid_base_urls_are_rejected(base_url: str) -> None:
    with pytest.raises(ValueError):
        OllamaProvider(base_url=base_url)


def test_provider_implements_existing_contract() -> None:
    provider = OllamaProvider()

    try:
        assert isinstance(provider, object)
        assert hasattr(provider, "complete")
    finally:
        asyncio.run(provider.aclose())


def test_chat_request_and_roles_are_preserved() -> None:
    request = _sample_request()

    assert request.messages[0].role == MessageRole.SYSTEM
    assert request.messages[1].role == MessageRole.USER
    assert request.model == "test-model"
