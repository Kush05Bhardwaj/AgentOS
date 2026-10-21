"""Construct providers from resolved AgentOS settings."""

import os
from collections.abc import Mapping

from agentos.config import ConfigurationError, ProviderConfig, Settings
from agentos.providers.adapters import (
    OllamaProvider,
    OpenAICompatibleProvider,
)
from agentos.providers.base import ChatProvider

SUPPORTED_PROVIDERS = ("ollama", "openai_compatible")


def _resolve_api_key(
    config: ProviderConfig,
    environment: Mapping[str, str],
) -> str | None:
    """Resolve a provider credential through its configured environment name."""
    variable_name = config.api_key_env

    if variable_name is None:
        return None

    if variable_name not in environment:
        raise ConfigurationError(
            f"Provider credential environment variable '{variable_name}' is not set."
        )

    api_key = environment[variable_name]

    if not api_key.strip():
        raise ConfigurationError(
            f"Provider credential environment variable '{variable_name}' is empty."
        )

    return api_key.strip()


def create_provider(
    settings: Settings,
    *,
    provider_name: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> ChatProvider:
    """Create the configured provider without making a network request.

    Args:
        settings: Resolved AgentOS settings.
        provider_name: Optional provider override. When omitted,
            settings.default_provider is used.
        environ: Optional environment mapping, primarily for testing.
            Defaults to the current process environment.

    Raises:
        ConfigurationError: If no provider is selected, the name is
            unsupported, or provider configuration is invalid.
    """
    environment = os.environ if environ is None else environ

    selected_name = provider_name if provider_name is not None else settings.default_provider

    if not isinstance(selected_name, str) or not selected_name.strip():
        raise ConfigurationError(
            "No provider is selected. Configure [defaults].provider "
            "or pass provider_name explicitly."
        )

    selected_name = selected_name.strip()

    if selected_name not in SUPPORTED_PROVIDERS:
        supported = ", ".join(SUPPORTED_PROVIDERS)
        raise ConfigurationError(
            f"Unknown provider '{selected_name}'. Supported providers: {supported}."
        )

    config = settings.providers.get(selected_name, ProviderConfig())

    try:
        if selected_name == "ollama":
            if config.api_key_env is not None:
                raise ConfigurationError(
                    "The Ollama adapter does not currently support "
                    "api_key_env. Remove that setting for Ollama."
                )

            if config.base_url is None:
                return OllamaProvider()

            return OllamaProvider(base_url=config.base_url)

        api_key = _resolve_api_key(config, environment)

        if config.base_url is None:
            return OpenAICompatibleProvider(api_key=api_key)

        return OpenAICompatibleProvider(
            base_url=config.base_url,
            api_key=api_key,
        )

    except ConfigurationError:
        raise
    except ValueError as exc:
        raise ConfigurationError(
            f"Invalid configuration for provider '{selected_name}': {exc}"
        ) from exc
