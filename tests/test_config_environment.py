"""Tests for AgentOS environment-variable configuration."""

from pathlib import Path

import pytest

import agentos.config.loader as loader
from agentos.config import ConfigurationError, Settings, load_settings


def test_environment_overrides_toml_values(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        """
[general]
max_steps = 3
max_concurrency = 1

[defaults]
provider = "ollama"
model = "toml-model"
""",
        encoding="utf-8",
    )

    workspace = tmp_path / "my workspace"

    settings = load_settings(
        config_file,
        environ={
            "AGENTOS_DEFAULT_PROVIDER": "openai_compatible",
            "AGENTOS_DEFAULT_MODEL": "environment-model",
            "AGENTOS_MAX_STEPS": "12",
            "AGENTOS_MAX_CONCURRENCY": "4",
            "AGENTOS_REQUEST_TIMEOUT_SECONDS": "45",
            "AGENTOS_MAX_TOOL_OUTPUT_CHARS": "15000",
            "AGENTOS_WORKSPACE": str(workspace),
        },
    )

    assert settings.default_provider == "openai_compatible"
    assert settings.default_model == "environment-model"
    assert settings.general.max_steps == 12
    assert settings.general.max_concurrency == 4
    assert settings.general.request_timeout_seconds == 45
    assert settings.general.max_tool_output_chars == 15000
    assert settings.general.workspace == workspace


def test_environment_overrides_apply_without_toml(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        loader,
        "default_config_path",
        lambda: tmp_path / "missing.toml",
    )

    settings = load_settings(
        environ={"AGENTOS_MAX_STEPS": "10"},
    )

    assert settings.general.max_steps == 10
    assert settings.default_provider is None


@pytest.mark.parametrize(
    "value",
    ["not-a-number", "", "1.5", "1_0"],
)
def test_invalid_integer_environment_value_is_rejected(
    value: str,
) -> None:
    with pytest.raises(ConfigurationError):
        load_settings(
            environ={"AGENTOS_MAX_STEPS": value},
        )


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("AGENTOS_MAX_STEPS", "65"),
        ("AGENTOS_MAX_CONCURRENCY", "0"),
        ("AGENTOS_REQUEST_TIMEOUT_SECONDS", "601"),
        ("AGENTOS_MAX_TOOL_OUTPUT_CHARS", "100001"),
    ],
)
def test_out_of_range_environment_value_is_rejected(
    name: str,
    value: str,
) -> None:
    with pytest.raises(ConfigurationError):
        load_settings(environ={name: value})


@pytest.mark.parametrize(
    "name",
    ["AGENTOS_DEFAULT_PROVIDER", "AGENTOS_DEFAULT_MODEL"],
)
def test_empty_string_environment_override_is_rejected(
    name: str,
) -> None:
    with pytest.raises(ConfigurationError):
        load_settings(environ={name: "  "})


def test_environment_does_not_override_unspecified_values(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        """
[defaults]
provider = "ollama"
model = "toml-model"
""",
        encoding="utf-8",
    )

    settings = load_settings(config_file, environ={})

    assert settings.default_provider == "ollama"
    assert settings.default_model == "toml-model"


def test_empty_environment_uses_builtin_defaults() -> None:
    settings = load_settings(environ={})

    assert settings == Settings()
