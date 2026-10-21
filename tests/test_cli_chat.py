"""Tests for the agentos chat command."""

from dataclasses import replace

import pytest
from typer.testing import CliRunner

import agentos.cli as cli
from agentos.config import ConfigurationError, Settings
from agentos.providers.errors import ProviderError
from agentos.providers.models import ChatMessage, ChatResponse, FinishReason

runner = CliRunner()

AGENTOS_ENV_VARS = (
    "AGENTOS_CONFIG",
    "AGENTOS_WORKSPACE",
    "AGENTOS_DEFAULT_PROVIDER",
    "AGENTOS_DEFAULT_MODEL",
    "AGENTOS_MAX_STEPS",
    "AGENTOS_MAX_CONCURRENCY",
    "AGENTOS_REQUEST_TIMEOUT_SECONDS",
    "AGENTOS_MAX_TOOL_OUTPUT_CHARS",
)


@pytest.fixture(autouse=True)
def clean_agentos_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep shell environment state out of CLI tests."""
    for name in AGENTOS_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def configured_settings() -> Settings:
    """Build settings that resolve without any real configuration file."""
    return Settings(
        default_provider="ollama",
        default_model="general-model",
    )


def test_second_request_includes_conversation_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = configured_settings()
    monkeypatch.setattr(cli, "load_settings", lambda config_path=None: settings)

    calls: list[tuple[ChatMessage, ...]] = []

    async def fake_complete_chat(
        settings_arg: Settings,
        messages: tuple[ChatMessage, ...],
        **kwargs: object,
    ) -> ChatResponse:
        calls.append(messages)
        text = "First response" if len(calls) == 1 else "Second response"
        return ChatResponse(text=text, model="general-model", finish_reason=FinishReason.STOP)

    monkeypatch.setattr(cli, "complete_chat", fake_complete_chat)

    result = runner.invoke(
        cli.app,
        ["chat"],
        input="First prompt\nSecond prompt\n/exit\n",
    )

    assert result.exit_code == 0, result.output
    assert len(calls) == 2

    assert calls[0] == (ChatMessage(role="user", content="First prompt"),)
    assert calls[1] == (
        ChatMessage(role="user", content="First prompt"),
        ChatMessage(role="assistant", content="First response"),
        ChatMessage(role="user", content="Second prompt"),
    )

    assert "First response" in result.output
    assert "Second response" in result.output
    assert "Chat ended." in result.output


@pytest.mark.parametrize("command", ["/exit", "/quit"])
def test_exit_commands_end_session_without_another_call(
    monkeypatch: pytest.MonkeyPatch,
    command: str,
) -> None:
    settings = configured_settings()
    monkeypatch.setattr(cli, "load_settings", lambda config_path=None: settings)

    calls: list[object] = []

    async def fake_complete_chat(
        settings_arg: Settings,
        messages: tuple[ChatMessage, ...],
        **kwargs: object,
    ) -> ChatResponse:
        calls.append(messages)
        return ChatResponse(text="Hello", model="general-model")

    monkeypatch.setattr(cli, "complete_chat", fake_complete_chat)

    result = runner.invoke(
        cli.app,
        ["chat"],
        input=f"Hello\n{command}\n",
    )

    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert "Chat ended." in result.output


def test_blank_input_is_ignored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = configured_settings()
    monkeypatch.setattr(cli, "load_settings", lambda config_path=None: settings)

    async def unexpected_call(*args: object, **kwargs: object) -> ChatResponse:
        pytest.fail("Blank input must not trigger a model request.")

    monkeypatch.setattr(cli, "complete_chat", unexpected_call)

    result = runner.invoke(
        cli.app,
        ["chat"],
        input="   \n/exit\n",
    )

    assert result.exit_code == 0, result.output
    assert "Chat ended." in result.output


def test_global_overrides_and_agent_reach_the_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = configured_settings()
    monkeypatch.setattr(cli, "load_settings", lambda config_path=None: settings)

    captured: dict[str, object] = {}

    async def fake_complete_chat(
        settings_arg: Settings,
        messages: tuple[ChatMessage, ...],
        *,
        agent_name: str | None = None,
        provider_override: str | None = None,
        model_override: str | None = None,
    ) -> ChatResponse:
        captured["settings"] = settings_arg
        captured["agent_name"] = agent_name
        captured["provider_override"] = provider_override
        captured["model_override"] = model_override
        return ChatResponse(text="Hello", model="cli-model")

    monkeypatch.setattr(cli, "complete_chat", fake_complete_chat)

    result = runner.invoke(
        cli.app,
        ["--provider", "ollama", "--model", "cli-model", "chat", "--agent", "coder"],
        input="Hello\n/exit\n",
    )

    assert result.exit_code == 0, result.output
    assert captured["agent_name"] == "coder"
    assert captured["provider_override"] == "ollama"
    assert captured["model_override"] == "cli-model"
    assert captured["settings"] == replace(
        settings,
        default_provider="ollama",
        default_model="cli-model",
    )


def test_configuration_failure_exits_with_code_two(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = configured_settings()
    monkeypatch.setattr(cli, "load_settings", lambda config_path=None: settings)

    async def fail_with_configuration_error(*args: object, **kwargs: object):
        raise ConfigurationError("No provider resolved.")

    monkeypatch.setattr(cli, "complete_chat", fail_with_configuration_error)

    result = runner.invoke(
        cli.app,
        ["chat"],
        input="Hello\n/exit\n",
    )

    assert result.exit_code == 2
    assert "Configuration error:" in result.output
    assert "No provider resolved" in result.output


def test_provider_failure_reports_error_and_allows_another_turn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = configured_settings()
    monkeypatch.setattr(cli, "load_settings", lambda config_path=None: settings)

    calls: list[tuple[ChatMessage, ...]] = []

    async def fake_complete_chat(
        settings_arg: Settings,
        messages: tuple[ChatMessage, ...],
        **kwargs: object,
    ) -> ChatResponse:
        calls.append(messages)
        if len(calls) == 1:
            raise ProviderError("Simulated failure.")
        return ChatResponse(text="Recovered.", model="general-model")

    monkeypatch.setattr(cli, "complete_chat", fake_complete_chat)

    result = runner.invoke(
        cli.app,
        ["chat"],
        input="Hello\nTry again\n/exit\n",
    )

    assert result.exit_code == 0, result.output
    assert "Provider error:" in result.output
    assert "Simulated failure." in result.output
    assert "Recovered." in result.output

    assert len(calls) == 2
    assert calls[1] == (ChatMessage(role="user", content="Try again"),)
