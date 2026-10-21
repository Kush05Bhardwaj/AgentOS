"""Command-line entry point for AgentOS."""

import asyncio
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from agentos import __version__
from agentos.agents import list_agents
from agentos.config import (
    ConfigurationError,
    Settings,
    apply_cli_overrides,
    load_settings,
)
from agentos.providers.errors import ProviderError
from agentos.providers.models import ChatMessage
from agentos.runtime import complete_chat

app = typer.Typer(
    name="agentos",
    help="A cross-platform terminal for coordinating specialized AI agents.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"AgentOS {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_version_callback,
            is_eager=True,
            help="Show the installed AgentOS version and exit.",
        ),
    ] = False,
    config: Annotated[
        Path | None,
        typer.Option("--config", help="Path to the TOML configuration file."),
    ] = None,
    provider: Annotated[
        str | None,
        typer.Option("--provider", help="Override the default provider."),
    ] = None,
    model: Annotated[
        str | None,
        typer.Option("--model", help="Override the default model."),
    ] = None,
    workspace: Annotated[
        Path | None,
        typer.Option("--workspace", help="Override the workspace directory."),
    ] = None,
    max_steps: Annotated[
        int | None,
        typer.Option("--max-steps", help="Override the maximum execution steps."),
    ] = None,
    max_concurrency: Annotated[
        int | None,
        typer.Option("--max-concurrency", help="Override concurrent execution limit."),
    ] = None,
    request_timeout_seconds: Annotated[
        int | None,
        typer.Option(
            "--request-timeout-seconds",
            help="Override the model request timeout in seconds.",
        ),
    ] = None,
    max_tool_output_chars: Annotated[
        int | None,
        typer.Option(
            "--max-tool-output-chars",
            help="Override the maximum tool output size.",
        ),
    ] = None,
) -> None:
    """AgentOS CLI."""
    try:
        settings = load_settings(config_path=config)

        ctx.obj = apply_cli_overrides(
            settings,
            provider=provider,
            model=model,
            workspace=workspace,
            max_steps=max_steps,
            max_concurrency=max_concurrency,
            request_timeout_seconds=request_timeout_seconds,
            max_tool_output_chars=max_tool_output_chars,
        )

    except ConfigurationError as exc:
        typer.echo(f"Configuration error: {exc}", err=True)
        raise typer.Exit(code=2) from exc


@app.command()
def agents() -> None:
    """List the built-in agent profiles."""
    table = Table(title="AgentOS built-in agents")
    table.add_column("Agent", style="cyan", no_wrap=True)
    table.add_column("Purpose")
    for profile in list_agents():
        table.add_row(profile.name, profile.summary)
    console.print(table)


@app.command()
def status() -> None:
    """Show which parts of the planned runtime are available."""
    console.print(f"[bold]AgentOS {__version__}[/bold]")
    console.print("Status: [yellow]foundation scaffold[/yellow]")
    console.print("Available: CLI, version output, built-in agent profile listing")
    console.print("Not implemented yet: model providers, orchestration, and tool execution")


@app.command()
def ask(
    ctx: typer.Context,
    prompt: Annotated[
        str,
        typer.Argument(help="The question or task to send to the model."),
    ],
    agent_name: Annotated[
        str | None,
        typer.Option(
            "--agent",
            help="Use a specific agent profile, such as coder or architect.",
        ),
    ] = None,
) -> None:
    """Send a single prompt to a configured AI model."""
    if not prompt.strip():
        typer.echo("Prompt cannot be empty or whitespace.", err=True)
        raise typer.Exit(code=2)

    settings = ctx.obj

    if not isinstance(settings, Settings):
        typer.echo("Configuration error: resolved settings are unavailable.", err=True)
        raise typer.Exit(code=2)

    # Preserve the explicit global CLI selections separately.
    # Otherwise, a per-agent override could incorrectly beat a CLI flag.
    parent_params = ctx.parent.params if ctx.parent is not None else {}

    provider_override = parent_params.get("provider")
    model_override = parent_params.get("model")

    try:
        response = asyncio.run(
            complete_chat(
                settings,
                (ChatMessage(role="user", content=prompt),),
                agent_name=agent_name,
                provider_override=provider_override,
                model_override=model_override,
            )
        )
    except ConfigurationError as exc:
        typer.echo(f"Configuration error: {exc}", err=True)
        raise typer.Exit(code=2) from exc
    except ProviderError as exc:
        typer.echo(f"Provider error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(response.text)
