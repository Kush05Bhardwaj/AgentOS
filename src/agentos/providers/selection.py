"""Resolve the effective provider and model for an agent."""

from dataclasses import dataclass

from agentos.config import ConfigurationError, Settings


@dataclass(frozen=True, slots=True)
class ModelSelection:
    """The effective provider/model pair for a task."""

    provider: str
    model: str
    agent_name: str | None = None


def _optional_value(name: str, value: object) -> str | None:
    """Normalize optional selection strings."""
    if value is None:
        return None

    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"{name} must be a non-empty string when provided.")

    return value.strip()


def resolve_model_selection(
    settings: Settings,
    *,
    agent_name: str | None = None,
    provider_override: str | None = None,
    model_override: str | None = None,
) -> ModelSelection:
    """Resolve provider and model independently.

    Precedence for each value:
        1. Explicit CLI override
        2. Agent-specific override
        3. Global resolved default

    This function performs no network I/O and does not create a provider.
    """
    agent_name = _optional_value("agent_name", agent_name)
    provider_override = _optional_value("provider_override", provider_override)
    model_override = _optional_value("model_override", model_override)

    agent_settings = settings.agents.get(agent_name) if agent_name is not None else None

    agent_provider = (
        _optional_value("agent.provider", agent_settings.provider)
        if agent_settings is not None
        else None
    )
    agent_model = (
        _optional_value("agent.model", agent_settings.model) if agent_settings is not None else None
    )

    global_provider = _optional_value("defaults.provider", settings.default_provider)
    global_model = _optional_value("defaults.model", settings.default_model)

    provider = provider_override or agent_provider or global_provider
    model = model_override or agent_model or global_model

    if provider is None:
        raise ConfigurationError(
            f"No provider resolved for agent '{agent_name or 'default'}'. "
            "Configure a global provider, an agent provider, "
            "or pass an explicit provider override."
        )

    if model is None:
        raise ConfigurationError(
            f"No model resolved for agent '{agent_name or 'default'}'. "
            "Configure a global model, an agent model, "
            "or pass an explicit model override."
        )

    return ModelSelection(
        provider=provider,
        model=model,
        agent_name=agent_name,
    )
