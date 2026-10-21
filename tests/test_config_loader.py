"""Tests for AgentOS TOML loading and config path discovery."""

from pathlib import Path

import pytest

import agentos.config.loader as loader
from agentos.config import (
    ConfigurationError,
    Settings,
    load_settings,
    resolve_config_path,
)


def test_default_path_uses_platform_config_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_dir = tmp_path / "user-config"
    monkeypatch.setattr(
        loader,
        "user_config_path",
        lambda *args, **kwargs: config_dir,
    )

    assert loader.default_config_path() == config_dir / "config.toml"


def test_missing_default_file_uses_builtin_defaults(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        loader,
        "default_config_path",
        lambda: tmp_path / "missing.toml",
    )

    assert load_settings(environ={}) == Settings()


def test_explicit_path_has_priority_over_environment(
    tmp_path: Path,
) -> None:
    explicit = tmp_path / "explicit.toml"
    environment_file = tmp_path / "environment.toml"

    explicit.write_text(
        '[defaults]\nmodel = "explicit-model"\n',
        encoding="utf-8",
    )
    environment_file.write_text(
        '[defaults]\nmodel = "environment-model"\n',
        encoding="utf-8",
    )

    settings = load_settings(
        explicit,
        environ={"AGENTOS_CONFIG": str(environment_file)},
    )

    assert settings.default_model == "explicit-model"


def test_environment_variable_selects_config_file(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "custom.toml"
    config_file.write_text(
        '[defaults]\nprovider = "ollama"\nmodel = "test-model"\n',
        encoding="utf-8",
    )

    settings = load_settings(
        environ={"AGENTOS_CONFIG": str(config_file)},
    )

    assert settings.default_provider == "ollama"
    assert settings.default_model == "test-model"


def test_missing_explicit_file_is_an_error(
    tmp_path: Path,
) -> None:
    with pytest.raises(ConfigurationError, match="not found"):
        load_settings(tmp_path / "missing.toml", environ={})


def test_missing_environment_selected_file_is_an_error(
    tmp_path: Path,
) -> None:
    missing_file = tmp_path / "missing.toml"

    with pytest.raises(ConfigurationError, match="not found"):
        load_settings(environ={"AGENTOS_CONFIG": str(missing_file)})


def test_empty_environment_path_is_an_error() -> None:
    with pytest.raises(ConfigurationError, match="empty path"):
        resolve_config_path(environ={"AGENTOS_CONFIG": "  "})


def test_loads_general_provider_and_agent_settings(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        """
[general]
workspace = "."
max_steps = 4
max_concurrency = 3

[defaults]
provider = "ollama"
model = "general-model"

[providers.ollama]
base_url = "http://localhost:11434"

[providers.openai_compatible]
base_url = "https://api.example.com/v1"
api_key_env = "EXAMPLE_API_KEY"

[agents.coder]
provider = "openai_compatible"
model = "coding-model"
""",
        encoding="utf-8",
    )

    settings = load_settings(config_file, environ={})

    assert settings.general.max_steps == 4
    assert settings.general.max_concurrency == 3
    assert settings.default_provider == "ollama"
    assert settings.default_model == "general-model"
    assert settings.providers["ollama"].base_url == "http://localhost:11434"
    assert settings.providers["openai_compatible"].api_key_env == "EXAMPLE_API_KEY"
    assert settings.agents["coder"].model == "coding-model"


def test_malformed_toml_is_an_error(tmp_path: Path) -> None:
    config_file = tmp_path / "broken.toml"
    config_file.write_text("setting = [", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="Invalid TOML"):
        load_settings(config_file, environ={})


def test_unknown_root_key_is_an_error(tmp_path: Path) -> None:
    config_file = tmp_path / "unknown.toml"
    config_file.write_text("misspelled_section = {}", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="Unknown key"):
        load_settings(config_file, environ={})


def test_unknown_general_key_is_an_error(tmp_path: Path) -> None:
    config_file = tmp_path / "unknown.toml"
    config_file.write_text(
        "[general]\nmax_concurency = 3\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="max_concurency"):
        load_settings(config_file, environ={})


def test_wrong_numeric_type_is_an_error(tmp_path: Path) -> None:
    config_file = tmp_path / "wrong-type.toml"
    config_file.write_text(
        '[general]\nmax_steps = "8"\n',
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="must be an integer"):
        load_settings(config_file, environ={})


def test_default_model_does_not_require_provider_credentials() -> None:
    settings = load_settings(environ={})

    assert settings.default_provider is None
    assert settings.default_model is None
