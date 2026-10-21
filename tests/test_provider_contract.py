"""Tests for the provider-neutral chat contract."""

import asyncio
import inspect

import pytest

from agentos.providers import (
    AuthenticationError,
    ChatMessage,
    ChatProvider,
    ChatRequest,
    ChatResponse,
    CompletionUsage,
    FinishReason,
    InvalidProviderResponseError,
    MessageRole,
    ModelUnavailableError,
    ProviderError,
    ProviderTimeoutError,
    RateLimitError,
)


class FakeProvider(ChatProvider):
    """In-memory provider used to verify the contract without a network."""

    def __init__(
        self,
        response: ChatResponse | None = None,
        error: Exception | None = None,
    ) -> None:
        self.requests: list[ChatRequest] = []
        self.response = response
        self.error = error

    async def complete(self, request: ChatRequest) -> ChatResponse:
        self.requests.append(request)

        if self.error is not None:
            raise self.error

        if self.response is None:
            raise AssertionError("FakeProvider was created without a response.")

        return self.response


def test_message_normalizes_role_strings() -> None:
    message = ChatMessage(role="user", content="Hello.")

    assert message.role is MessageRole.USER
    assert message.role == "user"


@pytest.mark.parametrize("role", ["system", "assistant", MessageRole.USER])
def test_message_accepts_supported_roles(role: object) -> None:
    message = ChatMessage(role=role, content="Hello.")

    assert message.role == role


def test_message_rejects_unknown_role() -> None:
    with pytest.raises(ValueError, match="role"):
        ChatMessage(role="tool", content="Hello.")


@pytest.mark.parametrize("content", ["", "   ", 42])
def test_message_rejects_blank_or_non_string_content(content: object) -> None:
    with pytest.raises(ValueError, match="content"):
        ChatMessage(role="user", content=content)


def test_request_defaults_and_normalizes_values() -> None:
    request = ChatRequest(
        model="  local-model  ",
        messages=[
            ChatMessage(role="system", content="You are helpful."),
            ChatMessage(role="user", content="Explain this function."),
        ],
    )

    assert request.model == "local-model"
    assert isinstance(request.messages, tuple)
    assert len(request.messages) == 2
    assert request.request_timeout_seconds == 120


def test_request_rejects_blank_model() -> None:
    with pytest.raises(ValueError, match="model"):
        ChatRequest(model="   ", messages=[ChatMessage(role="user", content="Hi.")])


def test_request_rejects_empty_messages() -> None:
    with pytest.raises(ValueError, match="at least one"):
        ChatRequest(model="local-model", messages=())


def test_request_rejects_non_message_entries() -> None:
    with pytest.raises(ValueError, match="ChatMessage"):
        ChatRequest(model="local-model", messages=("not a message",))


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("request_timeout_seconds", 0),
        ("request_timeout_seconds", 601),
        ("request_timeout_seconds", True),
    ],
)
def test_request_rejects_invalid_timeout(field_name: str, value: object) -> None:
    with pytest.raises(ValueError, match="between 1 and 600"):
        ChatRequest(
            model="local-model",
            messages=[ChatMessage(role="user", content="Hi.")],
            **{field_name: value},
        )


def test_response_normalizes_finish_reason() -> None:
    response = ChatResponse(text="Done.", model="local-model", finish_reason="length")

    assert response.finish_reason is FinishReason.LENGTH


def test_response_defaults_to_unknown_finish_reason() -> None:
    response = ChatResponse(text="Done.", model="local-model")

    assert response.finish_reason is FinishReason.UNKNOWN


def test_response_rejects_unrecognized_finish_reason() -> None:
    with pytest.raises(ValueError, match="finish reason"):
        ChatResponse(text="Done.", model="local-model", finish_reason="function_call")


def test_response_usage_is_optional() -> None:
    response = ChatResponse(text="Done.", model="local-model")

    assert response.usage is None


@pytest.mark.parametrize(
    "kwargs",
    [
        {"prompt_tokens": -1},
        {"completion_tokens": "3"},
        {"total_tokens": True},
    ],
)
def test_usage_rejects_invalid_token_counts(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError, match="Token counts"):
        CompletionUsage(**kwargs)


def test_response_rejects_blank_model() -> None:
    with pytest.raises(ValueError, match="model"):
        ChatResponse(text="Done.", model="")


@pytest.mark.parametrize(
    "error_type",
    [
        AuthenticationError,
        RateLimitError,
        ProviderTimeoutError,
        ModelUnavailableError,
        InvalidProviderResponseError,
    ],
)
def test_specific_errors_extend_provider_error(
    error_type: type[ProviderError],
) -> None:
    error = error_type("something went wrong")

    assert issubclass(error_type, ProviderError)
    assert isinstance(error, ProviderError)
    assert str(error) == "something went wrong"


def test_provider_complete_is_async() -> None:
    assert inspect.iscoroutinefunction(ChatProvider.complete)


def test_provider_requires_complete_implementation() -> None:
    class IncompleteProvider(ChatProvider):
        pass

    with pytest.raises(TypeError):
        IncompleteProvider()


def test_fake_provider_satisfies_contract() -> None:
    provider = FakeProvider(
        response=ChatResponse(
            text="Hello.",
            model="local-model",
            finish_reason="stop",
            usage=CompletionUsage(
                prompt_tokens=3,
                completion_tokens=2,
                total_tokens=5,
            ),
        )
    )
    request = ChatRequest(
        model="local-model",
        messages=[ChatMessage(role="user", content="Hi.")],
    )

    result = asyncio.run(provider.complete(request))

    assert isinstance(provider, ChatProvider)
    assert result.text == "Hello."
    assert result.model == "local-model"
    assert result.finish_reason is FinishReason.STOP
    assert provider.requests == [request]


def test_fake_provider_propagates_normalized_errors() -> None:
    provider = FakeProvider(error=RateLimitError("slow down"))
    request = ChatRequest(
        model="local-model",
        messages=[ChatMessage(role="user", content="Hi.")],
    )

    with pytest.raises(ProviderError, match="slow down"):
        asyncio.run(provider.complete(request))
