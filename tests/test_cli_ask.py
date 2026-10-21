"""Tests for the agentos ask command."""

from dataclasses import replace

import pytest
from typer.testing import CliRunner

import agentos.cli as cli
from agentos.config import AgentOverride, ConfigurationError, Settings
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


def test_ask_calls_runtime_and_prints_response(
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
    monkeypatch.setattr(
        cli,
        "load_settings",
        lambda config_path=None: settings,
    )

    captured: dict[str, object] = {}

    async def fake_complete_chat(
        settings_arg: Settings,
        messages: tuple[ChatMessage, ...],
        *,
        agent_name: str | None = None,
        provider_override: str | None = None,
        model_override: str | None = None,
        environ: object = None,
    ) -> ChatResponse:
        captured["settings"] = settings_arg
        captured["messages"] = messages
        captured["agent_name"] = agent_name
        captured["provider_override"] = provider_override
        captured["model_override"] = model_override

        return ChatResponse(
            text="Decorators wrap or modify functions.",
            model="fake-model",
            finish_reason=FinishReason.STOP,
        )

    monkeypatch.setattr(cli, "complete_chat", fake_complete_chat)

    result = runner.invoke(
        cli.app,
        [
            "--provider",
            "ollama",
            "--model",
            "cli-model",
            "ask",
            "Explain decorators",
            "--agent",
            "coder",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Decorators wrap or modify functions." in result.output

    assert captured["settings"] == replace(
        settings,
        default_provider="ollama",
        default_model="cli-model",
    )
    assert captured["agent_name"] == "coder"
    assert captured["provider_override"] == "ollama"
    assert captured["model_override"] == "cli-model"
    assert captured["messages"] == (ChatMessage(role="user", content="Explain decorators"),)


def test_ask_uses_global_defaults_when_no_agent_is_given(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        default_provider="ollama",
        default_model="general-model",
    )
    monkeypatch.setattr(
        cli,
        "load_settings",
        lambda config_path=None: settings,
    )

    captured: dict[str, object] = {}

    async def fake_complete_chat(
        settings_arg: Settings,
        messages: tuple[ChatMessage, ...],
        **kwargs: object,
    ) -> ChatResponse:
        captured["kwargs"] = kwargs
        return ChatResponse(
            text="Hello from the model",
            model="general-model",
        )

    monkeypatch.setattr(cli, "complete_chat", fake_complete_chat)

    result = runner.invoke(cli.app, ["ask", "Hello"])

    assert result.exit_code == 0, result.output
    assert "Hello from the model" in result.output

    kwargs = captured["kwargs"]
    assert isinstance(kwargs, dict)
    assert kwargs["agent_name"] is None
    assert kwargs["provider_override"] is None
    assert kwargs["model_override"] is None


@pytest.mark.parametrize("prompt", ["", "   ", "\t"])
def test_ask_rejects_empty_prompt(prompt: str) -> None:
    result = runner.invoke(cli.app, ["ask", prompt])

    assert result.exit_code == 2
    assert "Prompt cannot be empty" in result.output


def test_ask_reports_configuration_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cli,
        "load_settings",
        lambda config_path=None: Settings(),
    )

    async def fail_with_configuration_error(*args: object, **kwargs: object):
        raise ConfigurationError("No provider resolved.")

    monkeypatch.setattr(
        cli,
        "complete_chat",
        fail_with_configuration_error,
    )

    result = runner.invoke(cli.app, ["ask", "Hello"])

    assert result.exit_code == 2
    assert "Configuration error:" in result.output
    assert "No provider resolved" in result.output


def test_ask_reports_provider_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cli,
        "load_settings",
        lambda config_path=None: Settings(
            default_provider="ollama",
            default_model="test-model",
        ),
    )

    async def fail_with_provider_error(*args: object, **kwargs: object):
        raise ProviderError("Simulated provider failure.")

    monkeypatch.setattr(
        cli,
        "complete_chat",
        fail_with_provider_error,
    )

    result = runner.invoke(cli.app, ["ask", "Hello"])

    assert result.exit_code == 1
    assert "Provider error:" in result.output
    assert "Simulated provider failure" in result.output
