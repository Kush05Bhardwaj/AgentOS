"""Tests for the single-request AgentOS runtime."""

import asyncio
from collections.abc import Mapping

import pytest

import agentos.runtime.chat as chat_runtime
from agentos.config import (
    AgentOverride,
    ConfigurationError,
    GeneralSettings,
    Settings,
)
from agentos.providers.base import ChatProvider
from agentos.providers.errors import RateLimitError
from agentos.providers.models import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    FinishReason,
)


class FakeProvider(ChatProvider):
    """An offline provider that records requests and resource cleanup."""

    def __init__(
        self,
        response: ChatResponse | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self.response = response or ChatResponse(
            text="Fake response",
            model="fake-model",
            finish_reason=FinishReason.STOP,
        )
        self.error = error
        self.request: ChatRequest | None = None
        self.closed = False

    async def complete(self, request: ChatRequest) -> ChatResponse:
        self.request = request
        if self.error is not None:
            raise self.error
        return self.response

    async def aclose(self) -> None:
        self.closed = True


def sample_messages() -> tuple[ChatMessage, ...]:
    return (
        ChatMessage(
            role="system",
            content="You are a helpful developer assistant.",
        ),
        ChatMessage(
            role="user",
            content="Explain Python decorators.",
        ),
    )


def test_runtime_uses_agent_selection_and_closes_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        general=GeneralSettings(request_timeout_seconds=45),
        default_provider="ollama",
        default_model="general-model",
        agents={
            "coder": AgentOverride(model="coding-model"),
        },
    )

    fake = FakeProvider()
    captured: dict[str, object] = {}

    def fake_factory(
        settings_arg: Settings,
        *,
        provider_name: str | None = None,
        environ: Mapping[str, str] | None = None,
    ) -> ChatProvider:
        captured["settings"] = settings_arg
        captured["provider_name"] = provider_name
        captured["environ"] = environ
        return fake

    monkeypatch.setattr(chat_runtime, "create_provider", fake_factory)

    environment = {"TEST_PROVIDER_KEY": "offline-test-value"}

    response = asyncio.run(
        chat_runtime.complete_chat(
            settings,
            sample_messages(),
            agent_name="coder",
            environ=environment,
        )
    )

    assert response is fake.response
    assert captured["settings"] is settings
    assert captured["provider_name"] == "ollama"
    assert captured["environ"] is environment

    assert fake.request is not None
    assert fake.request.model == "coding-model"
    assert fake.request.request_timeout_seconds == 45
    assert fake.request.messages == sample_messages()
    assert fake.closed


def test_explicit_overrides_take_precedence_over_agent_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        default_provider="ollama",
        default_model="general-model",
        agents={
            "coder": AgentOverride(
                provider="openai_compatible",
                model="coding-model",
            ),
        },
    )

    fake = FakeProvider()
    captured: dict[str, object] = {}

    def fake_factory(
        settings_arg: Settings,
        *,
        provider_name: str | None = None,
        environ: Mapping[str, str] | None = None,
    ) -> ChatProvider:
        captured["provider_name"] = provider_name
        return fake

    monkeypatch.setattr(chat_runtime, "create_provider", fake_factory)

    asyncio.run(
        chat_runtime.complete_chat(
            settings,
            sample_messages(),
            agent_name="coder",
            provider_override="ollama",
            model_override="cli-model",
            environ={},
        )
    )

    assert captured["provider_name"] == "ollama"
    assert fake.request is not None
    assert fake.request.model == "cli-model"
    assert fake.closed


def test_runtime_uses_global_defaults_without_agent_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        default_provider="ollama",
        default_model="general-model",
    )

    fake = FakeProvider()

    monkeypatch.setattr(
        chat_runtime,
        "create_provider",
        lambda *args, **kwargs: fake,
    )

    asyncio.run(
        chat_runtime.complete_chat(
            settings,
            sample_messages(),
            environ={},
        )
    )

    assert fake.request is not None
    assert fake.request.model == "general-model"
    assert fake.closed


def test_missing_selection_fails_before_provider_creation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_factory(*args: object, **kwargs: object) -> ChatProvider:
        pytest.fail("Provider must not be created when selection is invalid.")

    monkeypatch.setattr(
        chat_runtime,
        "create_provider",
        unexpected_factory,
    )

    with pytest.raises(ConfigurationError, match="No provider resolved"):
        asyncio.run(
            chat_runtime.complete_chat(
                Settings(),
                sample_messages(),
                environ={},
            )
        )


def test_provider_error_propagates_and_provider_is_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeProvider(error=RateLimitError("Simulated rate limit"))

    monkeypatch.setattr(
        chat_runtime,
        "create_provider",
        lambda *args, **kwargs: fake,
    )

    settings = Settings(
        default_provider="ollama",
        default_model="test-model",
    )

    with pytest.raises(RateLimitError, match="Simulated rate limit"):
        asyncio.run(
            chat_runtime.complete_chat(
                settings,
                sample_messages(),
                environ={},
            )
        )

    assert fake.closed
