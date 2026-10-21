"""Smoke tests for the AgentOS CLI."""

from typer.testing import CliRunner

from agentos import __version__
from agentos.cli import app

runner = CliRunner()


def test_help_lists_commands() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "agents" in result.stdout
    assert "status" in result.stdout


def test_version_option() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert f"AgentOS {__version__}" in result.stdout


def test_agents_command_lists_builtin_profiles() -> None:
    result = runner.invoke(app, ["agents"])

    assert result.exit_code == 0
    for agent in ("architect", "coder", "researcher", "reviewer"):
        assert agent in result.stdout


def test_status_is_honest_about_unimplemented_runtime() -> None:
    result = runner.invoke(app, ["status"])

    assert result.exit_code == 0
    assert "foundation scaffold" in result.stdout
    assert "Not implemented yet" in result.stdout
