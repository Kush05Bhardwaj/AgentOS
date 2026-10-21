"""Typed configuration models and basic validation for AgentOS."""

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from agentos.config.defaults import (
    DEFAULT_MAX_CONCURRENCY,
    DEFAULT_MAX_STEPS,
    DEFAULT_MAX_TOOL_OUTPUT_CHARS,
    DEFAULT_REQUEST_TIMEOUT_SECONDS,
    MAX_CONCURRENCY_MAXIMUM,
    MAX_CONCURRENCY_MINIMUM,
    MAX_STEPS_MAXIMUM,
    MAX_STEPS_MINIMUM,
    MAX_TOOL_OUTPUT_MAXIMUM,
    MAX_TOOL_OUTPUT_MINIMUM,
    REQUEST_TIMEOUT_MAXIMUM,
    REQUEST_TIMEOUT_MINIMUM,
)


def _validate_integer(
    name: str,
    value: int,
    minimum: int,
    maximum: int,
) -> None:
    """Require an integer within an inclusive range."""
    # bool is a subclass of int in Python, so reject it explicitly.
    if type(value) is not int:
        raise ValueError(f"{name} must be an integer.")

    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}.")


def _validate_optional_text(name: str, value: str | None) -> None:
    """Allow None, but reject empty or whitespace-only strings."""
    if value is not None and (not isinstance(value, str) or not value.strip()):
        raise ValueError(f"{name} must be a non-empty string when provided.")


@dataclass(frozen=True, slots=True)
class GeneralSettings:
    """Application-wide operational limits and workspace."""

    workspace: Path = field(default_factory=Path.cwd)
    max_steps: int = DEFAULT_MAX_STEPS
    max_concurrency: int = DEFAULT_MAX_CONCURRENCY
    request_timeout_seconds: int = DEFAULT_REQUEST_TIMEOUT_SECONDS
    max_tool_output_chars: int = DEFAULT_MAX_TOOL_OUTPUT_CHARS

    def __post_init__(self) -> None:
        """Normalize the workspace path and validate execution limits."""
        try:
            workspace = Path(self.workspace).expanduser()
        except (TypeError, ValueError) as exc:
            raise ValueError("general.workspace must be a valid filesystem path.") from exc

        object.__setattr__(self, "workspace", workspace)

        _validate_integer(
            "general.max_steps",
            self.max_steps,
            MAX_STEPS_MINIMUM,
            MAX_STEPS_MAXIMUM,
        )
        _validate_integer(
            "general.max_concurrency",
            self.max_concurrency,
            MAX_CONCURRENCY_MINIMUM,
            MAX_CONCURRENCY_MAXIMUM,
        )
        _validate_integer(
            "general.request_timeout_seconds",
            self.request_timeout_seconds,
            REQUEST_TIMEOUT_MINIMUM,
            REQUEST_TIMEOUT_MAXIMUM,
        )
        _validate_integer(
            "general.max_tool_output_chars",
            self.max_tool_output_chars,
            MAX_TOOL_OUTPUT_MINIMUM,
            MAX_TOOL_OUTPUT_MAXIMUM,
        )


@dataclass(frozen=True, slots=True)
class ProviderConfig:
    """Configuration for a model provider endpoint."""

    base_url: str | None = None
    api_key_env: str | None = None

    def __post_init__(self) -> None:
        """Validate the endpoint URL and environment-variable name."""
        if self.base_url is not None:
            if (
                not isinstance(self.base_url, str)
                or not self.base_url.strip()
                or self.base_url != self.base_url.strip()
            ):
                raise ValueError(
                    "provider.base_url must be a non-empty URL without surrounding whitespace."
                )

            parsed = urlparse(self.base_url)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                raise ValueError("provider.base_url must be an absolute HTTP or HTTPS URL.")

            try:
                _ = parsed.port
            except ValueError as exc:
                raise ValueError("provider.base_url contains an invalid port.") from exc

        if self.api_key_env is not None:
            if not isinstance(self.api_key_env, str) or not re.fullmatch(
                r"[A-Z_][A-Z0-9_]*",
                self.api_key_env,
            ):
                raise ValueError(
                    "provider.api_key_env must be an uppercase environment variable name."
                )


@dataclass(frozen=True, slots=True)
class AgentOverride:
    """Optional provider/model overrides for a specific agent."""

    provider: str | None = None
    model: str | None = None

    def __post_init__(self) -> None:
        _validate_optional_text("agent.provider", self.provider)
        _validate_optional_text("agent.model", self.model)


@dataclass(frozen=True, slots=True)
class Settings:
    """Complete, provider-neutral AgentOS configuration."""

    general: GeneralSettings = field(default_factory=GeneralSettings)
    default_provider: str | None = None
    default_model: str | None = None
    providers: Mapping[str, ProviderConfig] = field(default_factory=dict)
    agents: Mapping[str, AgentOverride] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate optional defaults and named configuration sections."""
        _validate_optional_text("defaults.provider", self.default_provider)
        _validate_optional_text("defaults.model", self.default_model)

        for name, provider in self.providers.items():
            if not isinstance(name, str) or not name.strip():
                raise ValueError("Provider names must be non-empty strings.")
            if not isinstance(provider, ProviderConfig):
                raise ValueError(f"Provider '{name}' must use a ProviderConfig instance.")

        for name, agent in self.agents.items():
            if not isinstance(name, str) or not name.strip():
                raise ValueError("Agent names must be non-empty strings.")
            if not isinstance(agent, AgentOverride):
                raise ValueError(f"Agent '{name}' must use an AgentOverride instance.")
