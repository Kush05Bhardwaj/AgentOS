"""Tests for CLI configuration overrides."""

from pathlib import Path

import pytest

from agentos.config import (
    ConfigurationError,
    Settings,
    apply_cli_overrides,
    load_settings,
)


def test_cli_values_override_environment_and_toml(
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

    settings = load_settings(
        config_file,
        environ={
            "AGENTOS_DEFAULT_PROVIDER": "environment-provider",
            "AGENTOS_DEFAULT_MODEL": "environment-model",
        },
    )

    resolved = apply_cli_overrides(
        settings,
        provider="cli-provider",
        model="cli-model",
    )

    assert resolved.default_provider == "cli-provider"
    assert resolved.default_model == "cli-model"


def test_unspecified_cli_values_preserve_existing_settings() -> None:
    settings = Settings(
        default_provider="ollama",
        default_model="configured-model",
    )

    resolved = apply_cli_overrides(settings)

    assert resolved == settings


def test_cli_can_override_all_general_settings(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace with spaces"

    resolved = apply_cli_overrides(
        Settings(),
        workspace=workspace,
        max_steps=12,
        max_concurrency=4,
        request_timeout_seconds=45,
        max_tool_output_chars=15_000,
    )

    assert resolved.general.workspace == workspace
    assert resolved.general.max_steps == 12
    assert resolved.general.max_concurrency == 4
    assert resolved.general.request_timeout_seconds == 45
    assert resolved.general.max_tool_output_chars == 15_000


@pytest.mark.parametrize(
    "kwargs",
    [
        {"provider": ""},
        {"provider": "   "},
        {"model": ""},
        {"model": "   "},
        {"max_steps": 0},
        {"max_steps": 65},
        {"max_concurrency": 0},
        {"max_concurrency": 9},
        {"request_timeout_seconds": 601},
        {"max_tool_output_chars": 100_001},
    ],
)
def test_invalid_cli_overrides_are_rejected(
    kwargs: dict[str, object],
) -> None:
    with pytest.raises(ConfigurationError):
        apply_cli_overrides(Settings(), **kwargs)


def test_cli_overrides_do_not_mutate_original_settings() -> None:
    original = Settings(
        default_provider="ollama",
        default_model="original-model",
    )

    resolved = apply_cli_overrides(
        original,
        provider="another-provider",
        model="another-model",
    )

    assert original.default_provider == "ollama"
    assert original.default_model == "original-model"
    assert resolved.default_provider == "another-provider"
    assert resolved.default_model == "another-model"
