"""Load and validate AgentOS configuration files."""

import os
import re
import tomllib
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path

from platformdirs import user_config_path

from agentos.config.defaults import DEFAULT_CONFIG_FILENAME
from agentos.config.schema import (
    AgentOverride,
    GeneralSettings,
    ProviderConfig,
    Settings,
)

CONFIG_ENV_VAR = "AGENTOS_CONFIG"

_ENV_STRING_OVERRIDES = {
    "AGENTOS_DEFAULT_PROVIDER": "default_provider",
    "AGENTOS_DEFAULT_MODEL": "default_model",
}

_ENV_INTEGER_OVERRIDES = {
    "AGENTOS_MAX_STEPS": "max_steps",
    "AGENTOS_MAX_CONCURRENCY": "max_concurrency",
    "AGENTOS_REQUEST_TIMEOUT_SECONDS": "request_timeout_seconds",
    "AGENTOS_MAX_TOOL_OUTPUT_CHARS": "max_tool_output_chars",
}

_ROOT_KEYS = {"general", "defaults", "providers", "agents"}
_GENERAL_KEYS = {
    "workspace",
    "max_steps",
    "max_concurrency",
    "request_timeout_seconds",
    "max_tool_output_chars",
}


class ConfigurationError(ValueError):
    """Raised when AgentOS configuration cannot be loaded or validated."""


def default_config_path() -> Path:
    """Return the platform-specific default configuration path."""
    return Path(user_config_path("agentos", appauthor=False)) / DEFAULT_CONFIG_FILENAME


def resolve_config_path(
    explicit_path: str | Path | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> tuple[Path, bool]:
    """Resolve the config path and whether the user explicitly selected it.

    Precedence:
        1. Explicit CLI path
        2. AGENTOS_CONFIG environment variable
        3. Platform-specific default path
    """
    environment = os.environ if environ is None else environ

    if explicit_path is not None:
        value = str(explicit_path)
        if not value.strip():
            raise ConfigurationError("The --config path cannot be empty.")
        return Path(value).expanduser(), True

    if CONFIG_ENV_VAR in environment:
        value = environment[CONFIG_ENV_VAR]
        if not value.strip():
            raise ConfigurationError(f"{CONFIG_ENV_VAR} is set but contains an empty path.")
        return Path(value).expanduser(), True

    return default_config_path(), False


def _as_table(value: object, name: str) -> dict[str, object]:
    """Require a TOML table and normalize it to a dictionary."""
    if not isinstance(value, Mapping):
        raise ConfigurationError(f"'{name}' must be a TOML table.")

    table = dict(value)
    if not all(isinstance(key, str) for key in table):
        raise ConfigurationError(f"'{name}' contains an invalid key.")

    return table


def _check_keys(
    table: Mapping[str, object],
    allowed: set[str],
    section: str,
) -> None:
    """Reject misspelled or unsupported configuration keys."""
    unknown = sorted(set(table) - allowed)
    if unknown:
        names = ", ".join(unknown)
        raise ConfigurationError(f"Unknown key(s) in '{section}': {names}.")


def _optional_string(
    table: Mapping[str, object],
    key: str,
    section: str,
) -> str | None:
    """Read an optional string value without silently coercing types."""
    value = table.get(key)

    if value is None:
        return None

    if not isinstance(value, str):
        raise ConfigurationError(f"'{section}.{key}' must be a string.")

    return value


def parse_settings(document: object) -> Settings:
    """Convert parsed TOML data into validated settings objects."""
    root = _as_table(document, "root")
    _check_keys(root, _ROOT_KEYS, "root")

    try:
        general_data = _as_table(
            root.get("general", {}),
            "general",
        )
        _check_keys(general_data, _GENERAL_KEYS, "general")

        general_values: dict[str, object] = {}

        if "workspace" in general_data:
            workspace = general_data["workspace"]
            if not isinstance(workspace, str) or not workspace.strip():
                raise ConfigurationError("'general.workspace' must be a non-empty string.")
            general_values["workspace"] = Path(workspace)

        for key in (
            "max_steps",
            "max_concurrency",
            "request_timeout_seconds",
            "max_tool_output_chars",
        ):
            if key in general_data:
                value = general_data[key]
                if type(value) is not int:
                    raise ConfigurationError(f"'general.{key}' must be an integer.")
                general_values[key] = value

        general = GeneralSettings(**general_values)

        defaults_data = _as_table(
            root.get("defaults", {}),
            "defaults",
        )
        _check_keys(defaults_data, {"provider", "model"}, "defaults")

        providers_data = _as_table(
            root.get("providers", {}),
            "providers",
        )
        providers: dict[str, ProviderConfig] = {}

        for name, raw_config in providers_data.items():
            section = f"providers.{name}"
            provider_data = _as_table(raw_config, section)
            _check_keys(
                provider_data,
                {"base_url", "api_key_env"},
                section,
            )
            providers[name] = ProviderConfig(
                base_url=_optional_string(provider_data, "base_url", section),
                api_key_env=_optional_string(provider_data, "api_key_env", section),
            )

        agents_data = _as_table(root.get("agents", {}), "agents")
        agents: dict[str, AgentOverride] = {}

        for name, raw_config in agents_data.items():
            section = f"agents.{name}"
            agent_data = _as_table(raw_config, section)
            _check_keys(agent_data, {"provider", "model"}, section)

            agents[name] = AgentOverride(
                provider=_optional_string(agent_data, "provider", section),
                model=_optional_string(agent_data, "model", section),
            )

        return Settings(
            general=general,
            default_provider=_optional_string(defaults_data, "provider", "defaults"),
            default_model=_optional_string(defaults_data, "model", "defaults"),
            providers=providers,
            agents=agents,
        )

    except ConfigurationError:
        raise
    except (TypeError, ValueError) as exc:
        raise ConfigurationError(str(exc)) from exc


def apply_environment_overrides(
    settings: Settings,
    *,
    environ: Mapping[str, str] | None = None,
) -> Settings:
    """Apply supported environment-variable overrides to settings."""
    environment = os.environ if environ is None else environ

    general_overrides: dict[str, object] = {}
    settings_overrides: dict[str, str] = {}

    # String settings: default provider and model.
    for env_name, setting_name in _ENV_STRING_OVERRIDES.items():
        if env_name not in environment:
            continue

        value = environment[env_name]

        if not value.strip():
            raise ConfigurationError(f"{env_name} must not be empty.")

        settings_overrides[setting_name] = value.strip()

    # Workspace paths may contain spaces, so do not split them.
    if "AGENTOS_WORKSPACE" in environment:
        value = environment["AGENTOS_WORKSPACE"]

        if not value.strip():
            raise ConfigurationError("AGENTOS_WORKSPACE must not be empty.")

        general_overrides["workspace"] = Path(value).expanduser()

    # Numeric settings must be valid integers before schema validation.
    for env_name, setting_name in _ENV_INTEGER_OVERRIDES.items():
        if env_name not in environment:
            continue

        value = environment[env_name]

        if not re.fullmatch(r"[+-]?\d+", value):
            raise ConfigurationError(f"{env_name} must be an integer; received {value!r}.")

        general_overrides[setting_name] = int(value)

    try:
        general = replace(
            settings.general,
            **general_overrides,
        )

        return replace(
            settings,
            general=general,
            **settings_overrides,
        )

    except (TypeError, ValueError) as exc:
        raise ConfigurationError(str(exc)) from exc


def apply_cli_overrides(
    settings: Settings,
    *,
    provider: str | None = None,
    model: str | None = None,
    workspace: str | Path | None = None,
    max_steps: int | None = None,
    max_concurrency: int | None = None,
    request_timeout_seconds: int | None = None,
    max_tool_output_chars: int | None = None,
) -> Settings:
    """Apply explicit CLI values after environment and file settings."""
    general_overrides: dict[str, object] = {}
    settings_overrides: dict[str, str] = {}

    # Provider and model selections override configured defaults.
    for name, value in (
        ("default_provider", provider),
        ("default_model", model),
    ):
        if value is None:
            continue

        if not isinstance(value, str) or not value.strip():
            raise ConfigurationError(f"CLI override '{name}' must be a non-empty string.")

        settings_overrides[name] = value.strip()

    # Workspace paths may contain spaces. Never split them.
    if workspace is not None:
        if isinstance(workspace, str) and not workspace.strip():
            raise ConfigurationError("CLI override 'workspace' must not be empty.")

        try:
            general_overrides["workspace"] = Path(workspace).expanduser()
        except (TypeError, ValueError) as exc:
            raise ConfigurationError(f"Invalid CLI workspace path: {exc}") from exc

    # Leave unspecified values unchanged. GeneralSettings validates
    # types and allowed ranges when the replacement is constructed.
    for name, value in (
        ("max_steps", max_steps),
        ("max_concurrency", max_concurrency),
        ("request_timeout_seconds", request_timeout_seconds),
        ("max_tool_output_chars", max_tool_output_chars),
    ):
        if value is not None:
            general_overrides[name] = value

    try:
        updated_general = replace(
            settings.general,
            **general_overrides,
        )

        return replace(
            settings,
            general=updated_general,
            **settings_overrides,
        )

    except (TypeError, ValueError) as exc:
        raise ConfigurationError(str(exc)) from exc


def load_settings(
    config_path: str | Path | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> Settings:
    """Load settings from TOML, falling back to built-in defaults.

    A missing default config file is acceptable. A missing file explicitly
    selected by the caller or AGENTOS_CONFIG is an error.
    """
    path, must_exist = resolve_config_path(
        config_path,
        environ=environ,
    )

    try:
        with path.open("rb") as config_file:
            document = tomllib.load(config_file)

    except FileNotFoundError as exc:
        if must_exist:
            raise ConfigurationError(f"Configuration file not found: {path}") from exc
        return apply_environment_overrides(
            Settings(),
            environ=environ,
        )

    except tomllib.TOMLDecodeError as exc:
        raise ConfigurationError(f"Invalid TOML in '{path}': {exc}") from exc

    except UnicodeError as exc:
        raise ConfigurationError(f"Configuration file '{path}' is not valid UTF-8.") from exc

    except OSError as exc:
        raise ConfigurationError(f"Could not read configuration file '{path}': {exc}") from exc

    try:
        settings = parse_settings(document)
    except ConfigurationError as exc:
        raise ConfigurationError(f"{path}: {exc}") from exc

    return apply_environment_overrides(
        settings,
        environ=environ,
    )
