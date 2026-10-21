"""Tests for provider/model selection precedence."""

import pytest

from agentos.config import (
    AgentOverride,
    ConfigurationError,
    Settings,
)
from agentos.providers.selection import (
    ModelSelection,
    resolve_model_selection,
)


def test_global_defaults_are_selected() -> None:
    settings = Settings(
        default_provider="ollama",
        default_model="general-model",
    )

    result = resolve_model_selection(settings)

    assert result == ModelSelection(
        provider="ollama",
        model="general-model",
    )


def test_agent_overrides_replace_global_defaults() -> None:
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

    result = resolve_model_selection(settings, agent_name="coder")

    assert result.provider == "openai_compatible"
    assert result.model == "coding-model"
    assert result.agent_name == "coder"


def test_partial_agent_override_inherits_global_model() -> None:
    settings = Settings(
        default_provider="ollama",
        default_model="general-model",
        agents={
            "coder": AgentOverride(model="coding-model"),
        },
    )

    result = resolve_model_selection(settings, agent_name="coder")

    assert result.provider == "ollama"
    assert result.model == "coding-model"


def test_partial_agent_override_inherits_global_provider() -> None:
    settings = Settings(
        default_provider="ollama",
        default_model="general-model",
        agents={
            "coder": AgentOverride(provider="openai_compatible"),
        },
    )

    result = resolve_model_selection(settings, agent_name="coder")

    assert result.provider == "openai_compatible"
    assert result.model == "general-model"


def test_explicit_cli_values_override_agent_settings() -> None:
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

    result = resolve_model_selection(
        settings,
        agent_name="coder",
        provider_override="cli-provider",
        model_override="cli-model",
    )

    assert result.provider == "cli-provider"
    assert result.model == "cli-model"


def test_provider_and_model_overrides_are_independent() -> None:
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

    result = resolve_model_selection(
        settings,
        agent_name="coder",
        model_override="cli-model",
    )

    assert result.provider == "openai_compatible"
    assert result.model == "cli-model"


def test_unknown_agent_name_uses_global_defaults() -> None:
    settings = Settings(
        default_provider="ollama",
        default_model="general-model",
    )

    result = resolve_model_selection(
        settings,
        agent_name="custom-agent",
    )

    assert result.provider == "ollama"
    assert result.model == "general-model"
    assert result.agent_name == "custom-agent"


def test_missing_provider_is_rejected() -> None:
    settings = Settings(default_model="general-model")

    with pytest.raises(ConfigurationError, match="No provider resolved"):
        resolve_model_selection(settings)


def test_missing_model_is_rejected() -> None:
    settings = Settings(default_provider="ollama")

    with pytest.raises(ConfigurationError, match="No model resolved"):
        resolve_model_selection(settings)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"agent_name": ""},
        {"agent_name": "  "},
        {"provider_override": ""},
        {"provider_override": "  "},
        {"model_override": ""},
        {"model_override": "  "},
    ],
)
def test_blank_explicit_values_are_rejected(
    kwargs: dict[str, str],
) -> None:
    with pytest.raises(ConfigurationError):
        resolve_model_selection(
            Settings(
                default_provider="ollama",
                default_model="general-model",
            ),
            **kwargs,
        )


def test_whitespace_is_removed_from_selected_values() -> None:
    settings = Settings(
        default_provider=" ollama ",
        default_model=" general-model ",
    )

    result = resolve_model_selection(settings)

    assert result.provider == "ollama"
    assert result.model == "general-model"


def test_resolver_does_not_modify_settings() -> None:
    settings = Settings(
        default_provider="ollama",
        default_model="general-model",
        agents={
            "coder": AgentOverride(model="coding-model"),
        },
    )

    resolve_model_selection(
        settings,
        agent_name="coder",
        model_override="cli-model",
    )

    assert settings.default_model == "general-model"
    assert settings.agents["coder"].model == "coding-model"
