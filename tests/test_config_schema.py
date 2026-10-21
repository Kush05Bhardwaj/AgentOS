"""Tests for AgentOS configuration models."""

from pathlib import Path

import pytest

from agentos.config import (
    AgentOverride,
    GeneralSettings,
    ProviderConfig,
    Settings,
)


def test_general_settings_use_expected_defaults() -> None:
    settings = GeneralSettings()

    assert settings.workspace == Path.cwd()
    assert settings.max_steps == 8
    assert settings.max_concurrency == 2
    assert settings.request_timeout_seconds == 120
    assert settings.max_tool_output_chars == 20_000


def test_workspace_path_is_expanded() -> None:
    settings = GeneralSettings(workspace="~/agentos")

    assert settings.workspace == Path("~/agentos").expanduser()


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("max_steps", 0),
        ("max_steps", 65),
        ("max_steps", True),
        ("max_concurrency", 0),
        ("max_concurrency", 9),
        ("request_timeout_seconds", 0),
        ("request_timeout_seconds", 601),
        ("max_tool_output_chars", 1_023),
        ("max_tool_output_chars", 100_001),
    ],
)
def test_general_settings_reject_invalid_limits(
    field_name: str,
    value: object,
) -> None:
    with pytest.raises(ValueError):
        GeneralSettings(**{field_name: value})


def test_provider_config_accepts_http_endpoint() -> None:
    provider = ProviderConfig(
        base_url="http://localhost:11434",
        api_key_env=None,
    )

    assert provider.base_url == "http://localhost:11434"


@pytest.mark.parametrize(
    "url",
    [
        "",
        "not-a-url",
        "file:///tmp/model",
        "ftp://example.com/api",
        "http://",
    ],
)
def test_provider_config_rejects_invalid_urls(url: str) -> None:
    with pytest.raises(ValueError):
        ProviderConfig(base_url=url)


def test_provider_config_rejects_invalid_environment_variable_name() -> None:
    with pytest.raises(ValueError):
        ProviderConfig(api_key_env="my-api-key")


def test_agent_overrides_can_be_partial() -> None:
    override = AgentOverride(provider="ollama")

    assert override.provider == "ollama"
    assert override.model is None


def test_agent_override_rejects_blank_values() -> None:
    with pytest.raises(ValueError):
        AgentOverride(model="   ")


def test_settings_can_exist_without_a_provider() -> None:
    settings = Settings()

    assert settings.default_provider is None
    assert settings.default_model is None


def test_settings_accept_provider_and_agent_overrides() -> None:
    settings = Settings(
        default_provider="ollama",
        default_model="general-model",
        providers={
            "ollama": ProviderConfig(
                base_url="http://localhost:11434",
            ),
        },
        agents={
            "coder": AgentOverride(
                provider="openai_compatible",
                model="coding-model",
            ),
        },
    )

    assert settings.default_provider == "ollama"
    assert settings.providers["ollama"].base_url == ("http://localhost:11434")
    assert settings.agents["coder"].model == "coding-model"
