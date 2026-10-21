# AgentOS

**A cross-platform, multi-AI-agent terminal for developer workflows.**

AgentOS is a terminal-first environment for routing tasks to specialized AI agents, coordinating their work, and reviewing results from one consistent interface. The project is designed for **Linux and Windows from the first MVP**, with a modular architecture that can support additional platforms later.

> **Status:** Planning / pre-alpha. This repository plan and starter documentation do not represent an implemented or published product. Features described below are goals until they are built and tested.

## Vision

Use the right AI capability for the task without juggling disconnected chat sessions. AgentOS aims to provide:

- A command-line interface and interactive terminal UI.
- Specialized agents for coding, research, testing, data analysis, and operations.
- A provider layer that can route agents to configured model backends.
- A central orchestrator for task planning, agent handoffs, and result aggregation.
- Controlled tools for working with files, Git, tests, and shell commands.
- Persistent task/session history and observable execution logs.
- A platform abstraction that keeps the core usable on Windows and Linux.

## Design principles

1. **Cross-platform by default:** Linux and Windows are tested in CI from the first MVP.
2. **Model-provider agnostic:** agent logic should not depend on one model vendor.
3. **Explicit permissions:** filesystem writes and command execution must be bounded and visible.
4. **Inspectable execution:** users can see what an agent is doing, what tools it invoked, and what it returned.
5. **Small, composable components:** agents, providers, tools, and platform integrations have clear interfaces.
6. **Human control:** consequential actions require approval; agents should not silently execute arbitrary commands.
7. **Useful without orchestration:** users can invoke one agent directly before enabling multi-agent workflows.

## Proposed MVP

The MVP should prove the full cross-platform loop with a narrow feature set:

- Installable Python package with an `agentos` command.
- Interactive CLI/REPL and a small Textual terminal UI.
- Configuration file and environment-variable support for provider credentials.
- One provider integration first, behind a provider interface; add an OpenAI-compatible endpoint and Ollama where feasible.
- A small set of built-in agent profiles, initially `architect`, `coder`, `researcher`, and `reviewer`.
- Manual agent selection and basic automatic task routing.
- A minimal orchestrator that can create a plan, run bounded steps, and summarize results.
- Safe read-only filesystem tools plus explicitly approved write/command tools.
- Local session history using SQLite.
- Unit and integration tests on Linux and Windows.

See [`docs/MVP_SCOPE.md`](docs/MVP_SCOPE.md) for acceptance criteria and exclusions.

## Example UX (illustrative, not implemented)

```text
agentos
agentos agents
agentos ask --agent researcher "Compare SQLite and PostgreSQL for a local-first app"
agentos run "Review this repository and suggest the highest-priority fixes"
agentos sessions
agentos config
```

An interactive session might look like:

```text
AgentOS
  Agents: architect · coder · researcher · reviewer

agentos> Add input validation to the API

[architect] Creating a short implementation plan...
[coder] Waiting for approved implementation steps...
[reviewer] Will review the proposed diff after changes are made...

Plan ready. Approve execution? [y/N]
```

These commands and screens are examples of intended behavior; exact syntax may change during implementation.

## Proposed technology

| Area | Initial choice | Notes |
|---|---|---|
| Language | Python 3.11+ | Confirm supported versions during implementation. |
| CLI | Typer | Command parsing and help generation. |
| TUI | Textual + Rich | Cross-platform terminal interface; keep TUI optional if practical. |
| Async runtime | `asyncio` | Bounded concurrency and cancellation. |
| Configuration | TOML + environment variables | Never commit credentials. |
| Session storage | SQLite | Local history; no remote service required. |
| Tests | pytest | Run on Linux and Windows in CI. |
| Quality | Ruff + type checking | Exact type checker to be selected. |
| Packaging | `pyproject.toml` | Installable package and `agentos` entry point. |
| CI | GitHub Actions | Linux and Windows matrix. |

Dependencies and supported Python versions should be validated when the implementation begins.

## Architecture at a glance

```text
CLI / TUI
   |
Application services
   |
Orchestrator ---- Task router ---- Agent profiles
   |                  |                 |
Execution policy      Provider interface|
   |                  |                 |
Tool registry      Model adapters       |
   |                  |                 |
Platform adapters  Cloud/local models   |
   |
Filesystem / Git / tests / shell (permission-gated)

Shared services: configuration, SQLite sessions, logging, audit events
```

### Architecture boundaries

- `core/` contains orchestration and task logic, not OS-specific shell assumptions.
- `providers/` normalizes model requests and responses.
- `agents/` defines role instructions, tool access, and output expectations.
- `tools/` exposes bounded capabilities through typed interfaces.
- `platform/` isolates shell selection, process behavior, and platform paths.
- `memory/` stores session and task data locally.
- `cli/` and `tui/` are presentation layers over application services.

## Cross-platform contract

- Use `pathlib` for paths and platform-aware user config/data directories.
- Use `subprocess` with argument arrays, never build shell commands by concatenating untrusted strings.
- Do not assume Bash, `tmux`, `grep`, `sed`, or POSIX signals exist.
- Make PowerShell, Bash/Zsh, and terminal multiplexer integrations optional adapters.
- Set process timeouts, support cancellation, capture exit codes, and bound output.
- Test path handling, process execution, config locations, and CLI behavior on Windows and Linux.
- Document any feature that is unavailable on one platform rather than silently degrading.

## Safety and trust model

AgentOS can eventually access source code and run developer tools, so tool permissions are a core feature, not an afterthought.

- Start with read-only tools by default.
- Require confirmation before writing files, modifying Git state, or running commands.
- Show the command and working directory before execution.
- Apply timeouts and output limits.
- Never execute model-produced shell text automatically.
- Keep secrets out of logs and session transcripts.
- Treat repository content and tool output as untrusted input.
- Do not promise a security sandbox unless one is actually implemented and verified.

## Repository layout

See [`docs/REPOSITORY_STRUCTURE.md`](docs/REPOSITORY_STRUCTURE.md) for the proposed package tree and module responsibilities.

## Getting started

The project is currently at the planning stage. Once the initial implementation lands, this section should include verified installation and development commands. The expected developer workflow will be approximately:

```bash
# Create and activate a virtual environment using your OS's normal workflow.
python -m venv .venv

# Install in editable mode after pyproject.toml and package code exist.
python -m pip install -e ".[dev]"

# Run tests after the test suite is added.
python -m pytest
```

These commands are a planned workflow, not a claim that the package is already installable.

## Roadmap

1. **Foundation:** package skeleton, config, logging, CLI, Linux/Windows CI.
2. **Single-agent loop:** provider interface, one model adapter, agent profiles, streamed output.
3. **Controlled tools:** read-only filesystem access, approvals, safe command runner.
4. **Orchestration:** task plans, routing, bounded handoffs, final synthesis.
5. **TUI and sessions:** agent status view, cancellation, SQLite history.
6. **Hardening:** Windows/Linux integration tests, docs, packaging, security review, pre-release.

The issue-by-issue plan is in [`docs/GITHUB_ISSUE_ROADMAP.md`](docs/GITHUB_ISSUE_ROADMAP.md).

## Contributing

Contributions are welcome once the repository is initialized. Start with [`CONTRIBUTING.md`](CONTRIBUTING.md), check the roadmap, and open an issue before making a large architectural change.

## License

AgentOS is planned to be released under the [MIT License](LICENSE). The license file should be added before publishing or accepting contributions. This planning bundle includes a starter license file.

## Project status

This is a proposed design and documentation baseline. No GitHub repository has been created by producing these files, and no functionality should be assumed to exist until implementation and tests are added.
