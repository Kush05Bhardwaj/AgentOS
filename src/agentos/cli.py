"""Command-line entry point for AgentOS."""

from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from agentos import __version__
from agentos.agents import list_agents

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
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_version_callback,
            is_eager=True,
            help="Show the installed AgentOS version and exit.",
        ),
    ] = False,
) -> None:
    """AgentOS CLI."""
    del version


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
