"""Offline tests for the OpenAI-compatible provider adapter."""

import asyncio
import json
from collections.abc import Callable

import httpx
import pytest

from agentos.providers.adapters import OpenAICompatibleProvider
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


def sample_request() -> ChatRequest:
    return ChatRequest(
        model="test-model",
        messages=(
            ChatMessage(role="system", content="Be helpful."),
            ChatMessage(role="user", content="Explain Python."),
        ),
        request_timeout_seconds=30,
    )


def run_completion(
    handler: ResponseHandler,
    *,
    api_key: str | None = None,
    base_url: str = "https://api.example.com/v1",
) -> ChatResponse:
    async def execute() -> ChatResponse:
        transport = httpx.MockTransport(handler)

        async with httpx.AsyncClient(transport=transport) as client:
            provider = OpenAICompatibleProvider(
                base_url=base_url,
                api_key=api_key,
                client=client,
            )
            return await provider.complete(sample_request())

    return asyncio.run(execute())


def successful_response(
    request: httpx.Request,
) -> httpx.Response:
    return httpx.Response(
        200,
        request=request,
        json={
            "model": "test-model",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Python is a programming language.",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 7,
                "total_tokens": 17,
            },
        },
    )


def test_successful_completion_is_normalized() -> None:
    response = run_completion(successful_response)

    assert response == ChatResponse(
        text="Python is a programming language.",
        model="test-model",
        finish_reason=FinishReason.STOP,
        usage=CompletionUsage(
            prompt_tokens=10,
            completion_tokens=7,
            total_tokens=17,
        ),
    )


def test_request_endpoint_and_payload() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["payload"] = json.loads(request.content)
        captured["authorization"] = request.headers.get("Authorization")
        return successful_response(request)

    run_completion(handler, api_key="test-secret")

    assert captured["url"] == "https://api.example.com/v1/chat/completions"
    assert captured["authorization"] == "Bearer test-secret"

    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["model"] == "test-model"
    assert payload["stream"] is False
    assert payload["messages"] == [
        {"role": "system", "content": "Be helpful."},
        {"role": "user", "content": "Explain Python."},
    ]


def test_api_key_is_optional_for_local_compatible_endpoints() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "Authorization" not in request.headers
        return successful_response(request)

    run_completion(
        handler,
        base_url="http://localhost:8000/v1",
    )


def test_custom_model_from_response_is_preserved() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        response = successful_response(request)
        body = response.json()
        body["model"] = "actual-model"
        return httpx.Response(200, request=request, json=body)

    assert run_completion(handler).model == "actual-model"


def test_missing_usage_is_allowed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            request=request,
            json={
                "choices": [
                    {
                        "message": {"content": "Hello"},
                        "finish_reason": "stop",
                    }
                ]
            },
        )

    response = run_completion(handler)

    assert response.text == "Hello"
    assert response.model == "test-model"
    assert response.usage is None


def test_missing_total_token_count_is_calculated() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            request=request,
            json={
                "choices": [
                    {
                        "message": {"content": "Hello"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 8,
                    "completion_tokens": 4,
                },
            },
        )

    assert run_completion(handler).usage == CompletionUsage(
        prompt_tokens=8,
        completion_tokens=4,
        total_tokens=12,
    )


@pytest.mark.parametrize(
    ("reason", "expected"),
    [
        ("stop", FinishReason.STOP),
        ("length", FinishReason.LENGTH),
        ("content_filter", FinishReason.CONTENT_FILTER),
        ("tool_calls", FinishReason.UNKNOWN),
        ("future_reason", FinishReason.UNKNOWN),
    ],
)
def test_finish_reason_mapping(
    reason: str,
    expected: FinishReason,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        response = successful_response(request)
        body = response.json()
        body["choices"][0]["finish_reason"] = reason
        return httpx.Response(200, request=request, json=body)

    assert run_completion(handler).finish_reason == expected


@pytest.mark.parametrize(
    ("status", "error_type"),
    [
        (401, AuthenticationError),
        (403, AuthenticationError),
        (404, ModelUnavailableError),
        (429, RateLimitError),
        (408, ProviderTimeoutError),
        (504, ProviderTimeoutError),
        (400, ProviderError),
        (500, ProviderError),
        (503, ProviderError),
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
            json={"error": {"message": "simulated failure"}},
        )

    with pytest.raises(error_type):
        run_completion(handler)


def test_timeout_is_normalized() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("simulated timeout", request=request)

    with pytest.raises(ProviderTimeoutError, match="30 seconds"):
        run_completion(handler)


def test_connection_error_is_normalized() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(
            "simulated connection failure",
            request=request,
        )

    with pytest.raises(ProviderError, match="Could not connect"):
        run_completion(handler)


@pytest.mark.parametrize(
    "body",
    [
        b"not-json",
        b"null",
        b"[]",
        b'{"choices": []}',
        b'{"choices": [{}]}',
        b'{"choices": [{"message": {}}]}',
        b'{"choices": [{"message": {"content": 123}}]}',
        b'{"choices": [{"message": {"content": "Hello"}, "finish_reason": 12}]}',
        b'{"model": 12, "choices": [{"message": {"content": "Hello"}}]}',
        b'{"choices": [{"message": {"content": "Hello"}}], "usage": []}',
        b'{"choices": [{"message": {"content": "Hello"}}], "usage": {"prompt_tokens": -1}}',
        b'{"choices": [{"message": {"content": "Hello"}}], "usage": {"completion_tokens": true}}',
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
        run_completion(handler)


@pytest.mark.parametrize(
    "base_url",
    [
        "",
        "not-a-url",
        "ftp://example.com/v1",
        "http://",
        "https://user:password@example.com/v1",
        "https://example.com/v1?token=secret",
        "https://example.com/v1#fragment",
        "https://example.com:99999/v1",
    ],
)
def test_invalid_base_urls_are_rejected(base_url: str) -> None:
    with pytest.raises(ValueError):
        OpenAICompatibleProvider(base_url=base_url)


@pytest.mark.parametrize("api_key", ["", " ", "\t"])
def test_blank_api_keys_are_rejected(api_key: str) -> None:
    with pytest.raises(ValueError):
        OpenAICompatibleProvider(api_key=api_key)


def test_invalid_usage_values_are_rejected() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            request=request,
            json={
                "choices": [
                    {
                        "message": {"content": "Hello"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": "ten"},
            },
        )

    with pytest.raises(InvalidProviderResponseError):
        run_completion(handler)


def test_provider_can_be_used_as_an_async_context_manager() -> None:
    async def execute() -> None:
        async with OpenAICompatibleProvider() as provider:
            assert isinstance(provider, OpenAICompatibleProvider)

    asyncio.run(execute())


def test_chat_request_roles_are_preserved() -> None:
    request = sample_request()

    assert request.messages[0].role == MessageRole.SYSTEM
    assert request.messages[1].role == MessageRole.USER
