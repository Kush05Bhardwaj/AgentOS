"""Integration tests for CLI configuration options."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

import agentos.cli as cli
from agentos.config import Settings

runner = CliRunner()

_AGENTOS_ENV_VARS = (
    "AGENTOS_CONFIG",
    "AGENTOS_WORKSPACE",
    "AGENTOS_DEFAULT_PROVIDER",
    "AGENTOS_DEFAULT_MODEL",
    "AGENTOS_MAX_STEPS",
    "AGENTOS_MAX_CONCURRENCY",
    "AGENTOS_REQUEST_TIMEOUT_SECONDS",
    "AGENTOS_MAX_TOOL_OUTPUT_CHARS",
)


@pytest.fixture(autouse=True)
def clean_agentos_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prevent the developer's shell environment affecting CLI tests."""
    for name in _AGENTOS_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def test_help_shows_global_configuration_options() -> None:
    result = runner.invoke(cli.app, ["--help"])

    assert result.exit_code == 0
    for option in (
        "--config",
        "--provider",
        "--model",
        "--workspace",
        "--max-steps",
        "--max-concurrency",
        "--request-timeout-seconds",
        "--max-tool-output-chars",
    ):
        assert option in result.output


def test_global_options_resolve_through_the_cli(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        """
[general]
max_steps = 3
max_concurrency = 1

[defaults]
provider = "toml-provider"
model = "toml-model"
""",
        encoding="utf-8",
    )
    workspace = tmp_path / "workspace with spaces"

    resolved_settings: list[Settings] = []
    original_apply = cli.apply_cli_overrides

    def capture_resolved_settings(
        settings: Settings,
        **kwargs: object,
    ) -> Settings:
        resolved = original_apply(settings, **kwargs)
        resolved_settings.append(resolved)
        return resolved

    monkeypatch.setattr(
        cli,
        "apply_cli_overrides",
        capture_resolved_settings,
    )

    result = runner.invoke(
        cli.app,
        [
            "--config",
            str(config_file),
            "--provider",
            "cli-provider",
            "--model",
            "cli-model",
            "--workspace",
            str(workspace),
            "--max-steps",
            "11",
            "--max-concurrency",
            "5",
            "--request-timeout-seconds",
            "90",
            "--max-tool-output-chars",
            "30000",
            "agents",
        ],
        env={
            "AGENTOS_DEFAULT_PROVIDER": "environment-provider",
            "AGENTOS_DEFAULT_MODEL": "environment-model",
            "AGENTOS_MAX_STEPS": "9",
            "AGENTOS_MAX_CONCURRENCY": "4",
        },
    )

    assert result.exit_code == 0, result.output
    assert len(resolved_settings) == 1

    settings = resolved_settings[0]
    assert settings.default_provider == "cli-provider"
    assert settings.default_model == "cli-model"
    assert settings.general.workspace == workspace
    assert settings.general.max_steps == 11
    assert settings.general.max_concurrency == 5
    assert settings.general.request_timeout_seconds == 90
    assert settings.general.max_tool_output_chars == 30000


def test_invalid_config_exits_cleanly(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "broken.toml"
    config_file.write_text("setting = [", encoding="utf-8")

    result = runner.invoke(
        cli.app,
        ["--config", str(config_file), "agents"],
    )

    assert result.exit_code == 2
    assert "Configuration error:" in result.output
    assert "Invalid TOML" in result.output


def test_invalid_cli_limit_exits_cleanly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cli,
        "load_settings",
        lambda config_path=None: Settings(),
    )

    result = runner.invoke(
        cli.app,
        ["--max-steps", "65", "agents"],
    )

    assert result.exit_code == 2
    assert "Configuration error:" in result.output
    assert "between 1 and 64" in result.output
