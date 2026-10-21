# AgentOS

**A cross-platform, multi-AI-agent terminal for developer workflows.**

AgentOS is a terminal-first project designed to route tasks to specialized AI agents, coordinate their work, and present results in one consistent interface. Linux and Windows are first-class targets from the first MVP.

> **Status: Pre-alpha foundation.** The repository now contains an installable CLI scaffold and built-in agent profile metadata. Model providers, task orchestration, memory, and tool execution are not implemented yet.

## Vision

AgentOS aims to give developers one terminal command center for coding, debugging, research, testing, data analysis, and operations. Users will be able to choose an agent directly or ask an orchestrator to route a task to the right combination of agents.

## What works today

- Installable Python package with an `agentos` command.
- `agentos --help` and `agentos --version`.
- `agentos agents` lists the initial built-in profiles: architect, coder, researcher, and reviewer.
- `agentos status` reports the current scaffold status.
- Smoke tests run in a Linux/Windows GitHub Actions matrix.
- Ruff linting and formatting checks run in CI.

These are the initial foundation features. The CLI does **not** call an AI model yet.

## Planned capabilities

- Provider adapters for local and hosted models.
- Direct agent invocation and configurable model selection.
- Task planning, routing, bounded parallelism, and structured agent handoffs.
- Read-only repository tools, Git inspection, proposed diffs, and approval-gated actions.
- A Textual terminal UI with visible agent status and logs.
- SQLite-backed local session history.
- Clear execution limits, cancellation, and secret redaction.

## Built-in agent roles

| Agent | Intended responsibility |
|---|---|
| architect | Break a task into a plan and identify design trade-offs. |
| coder | Help implement focused code changes once model and tool execution exist. |
| researcher | Analyze supplied context and later support approved research tools. |
| reviewer | Review plans and diffs for issues, risks, and evidence. |

Profiles currently describe intended roles only; they do not run separate model instances.

## Quick start

Requires Python 3.11 or newer.

### Windows (PowerShell)

    git clone https://github.com/Kush05Bhardwaj/AgentOS.git
    Set-Location AgentOS
    py -3.11 -m venv .venv
    .venv/Scripts/python.exe -m pip install -e ".[dev]"
    .venv/Scripts/agentos.exe --help
    .venv/Scripts/agentos.exe agents
    .venv/Scripts/python.exe -m pytest

### Linux

    git clone https://github.com/Kush05Bhardwaj/AgentOS.git
    cd AgentOS
    python3.11 -m venv .venv
    .venv/bin/python -m pip install -e ".[dev]"
    .venv/bin/agentos --help
    .venv/bin/agentos agents
    .venv/bin/python -m pytest

See [Development Setup](docs/DEVELOPMENT.md) for more details.

## Technology choices

| Area | Initial choice |
|---|---|
| Language | Python 3.11+ |
| CLI | Typer + Rich |
| Async runtime | asyncio |
| Configuration | TOML + environment variables (planned) |
| Session storage | SQLite (planned) |
| Tests | pytest |
| Lint and format | Ruff |
| CI | GitHub Actions on Linux and Windows |

## Architecture principles

1. **Cross-platform by default.** Do not assume Bash, GNU utilities, POSIX signals, or tmux are installed.
2. **Provider agnostic.** Agent and orchestration contracts should not depend on a single model SDK.
3. **Human control.** File writes, Git mutations, and process execution will require explicit permissions and approval.
4. **Inspectability.** Show task status, tool requests, outcomes, errors, and bounded logs.
5. **Small interfaces.** Keep core orchestration separate from agents, providers, tools, storage, and platform adapters.
6. **Honest status.** Documentation must distinguish shipped behavior from planned capabilities.

## Repository map

- [MVP Scope](docs/MVP_SCOPE.md) — acceptance criteria and boundaries.
- [Repository Structure](docs/REPOSITORY_STRUCTURE.md) — target package layout and module responsibilities.
- [GitHub Issue Roadmap](docs/GITHUB_ISSUE_ROADMAP.md) — prioritized implementation backlog.
- [Development Setup](docs/DEVELOPMENT.md) — setup and local checks.
- [Contributing](CONTRIBUTING.md) — contribution workflow and coding guidance.
- [License](LICENSE) — MIT.

## Roadmap

1. **Foundation:** package metadata, CLI, tests, cross-platform CI.
2. **Single-agent loop:** configuration, provider contract, one provider, useful model-backed CLI request.
3. **Controlled tools:** workspace-confined reads, approvals, and safe command execution.
4. **Orchestration:** planning, task routing, handoffs, review, and synthesis.
5. **Terminal cockpit:** TUI, execution events, cancellation, and session history.
6. **Hardening:** cross-platform edge cases, security review, packaging, and pre-release.

See the issue roadmap for suggested scope and acceptance criteria. The identifiers in that document are planning labels, not GitHub issue numbers.

## Safety direction

AgentOS is intended to operate around developer files and tools. The project will start with read-only capabilities, keep work inside an explicitly configured workspace where applicable, apply timeouts/output limits, redact secrets, and require approval before side effects. The project will not claim to provide a security sandbox unless that isolation is implemented and verified.

## License

AgentOS is released under the MIT License. See [LICENSE](LICENSE).
