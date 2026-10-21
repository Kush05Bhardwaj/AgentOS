"""Tests for the AgentOS provider factory."""

import asyncio

import pytest

from agentos.config import ConfigurationError, ProviderConfig, Settings
from agentos.providers.adapters import (
    OllamaProvider,
    OpenAICompatibleProvider,
)
from agentos.providers.factory import create_provider


def close_provider(provider: object) -> None:
    """Close the client owned by an adapter instance."""
    asyncio.run(provider.aclose())


def test_factory_creates_ollama_from_default_provider() -> None:
    settings = Settings(
        default_provider="ollama",
        providers={
            "ollama": ProviderConfig(
                base_url="http://localhost:11435",
            ),
        },
    )

    provider = create_provider(settings, environ={})

    try:
        assert isinstance(provider, OllamaProvider)
        assert provider._base_url == "http://localhost:11435"
    finally:
        close_provider(provider)


def test_factory_uses_ollama_default_base_url() -> None:
    provider = create_provider(
        Settings(default_provider="ollama"),
        environ={},
    )

    try:
        assert isinstance(provider, OllamaProvider)
        assert provider._base_url == "http://localhost:11434"
    finally:
        close_provider(provider)


def test_factory_creates_openai_compatible_provider() -> None:
    settings = Settings(
        default_provider="openai_compatible",
        providers={
            "openai_compatible": ProviderConfig(
                base_url="https://api.example.com/v1",
            ),
        },
    )

    provider = create_provider(settings, environ={})

    try:
        assert isinstance(provider, OpenAICompatibleProvider)
        assert provider._base_url == "https://api.example.com/v1"
        assert provider._api_key is None
    finally:
        close_provider(provider)


def test_factory_uses_default_openai_compatible_url() -> None:
    provider = create_provider(
        Settings(default_provider="openai_compatible"),
        environ={},
    )

    try:
        assert isinstance(provider, OpenAICompatibleProvider)
        assert provider._base_url == "https://api.openai.com/v1"
    finally:
        close_provider(provider)


def test_factory_resolves_api_key_from_configured_environment_name() -> None:
    settings = Settings(
        default_provider="openai_compatible",
        providers={
            "openai_compatible": ProviderConfig(
                api_key_env="TEST_PROVIDER_KEY",
            ),
        },
    )

    provider = create_provider(
        settings,
        environ={"TEST_PROVIDER_KEY": "test-secret-value"},
    )

    try:
        assert isinstance(provider, OpenAICompatibleProvider)
        assert provider._api_key == "test-secret-value"
    finally:
        close_provider(provider)


def test_missing_credential_variable_is_a_configuration_error() -> None:
    settings = Settings(
        default_provider="openai_compatible",
        providers={
            "openai_compatible": ProviderConfig(
                api_key_env="MISSING_TEST_KEY",
            ),
        },
    )

    with pytest.raises(ConfigurationError, match="MISSING_TEST_KEY"):
        create_provider(settings, environ={})


def test_empty_credential_variable_is_a_configuration_error() -> None:
    settings = Settings(
        default_provider="openai_compatible",
        providers={
            "openai_compatible": ProviderConfig(
                api_key_env="TEST_PROVIDER_KEY",
            ),
        },
    )

    with pytest.raises(ConfigurationError, match="is empty"):
        create_provider(
            settings,
            environ={"TEST_PROVIDER_KEY": "   "},
        )


def test_provider_argument_overrides_default_provider() -> None:
    settings = Settings(default_provider="ollama")

    provider = create_provider(
        settings,
        provider_name="openai_compatible",
        environ={},
    )

    try:
        assert isinstance(provider, OpenAICompatibleProvider)
    finally:
        close_provider(provider)


def test_missing_provider_is_rejected() -> None:
    with pytest.raises(ConfigurationError, match="No provider is selected"):
        create_provider(Settings(), environ={})


def test_unknown_provider_is_rejected() -> None:
    with pytest.raises(ConfigurationError, match="Unknown provider"):
        create_provider(
            Settings(default_provider="some_provider"),
            environ={},
        )


def test_ollama_rejects_unsupported_credential_configuration() -> None:
    settings = Settings(
        default_provider="ollama",
        providers={
            "ollama": ProviderConfig(
                api_key_env="TEST_PROVIDER_KEY",
            ),
        },
    )

    with pytest.raises(ConfigurationError, match="does not currently support"):
        create_provider(
            settings,
            environ={"TEST_PROVIDER_KEY": "test-secret-value"},
        )


def test_invalid_adapter_configuration_becomes_configuration_error() -> None:
    settings = Settings(
        default_provider="openai_compatible",
        providers={
            "openai_compatible": ProviderConfig(
                base_url="https://user:password@example.com/v1",
            ),
        },
    )

    with pytest.raises(ConfigurationError, match="Invalid configuration"):
        create_provider(settings, environ={})
