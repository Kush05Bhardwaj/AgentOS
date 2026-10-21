# Contributing to AgentOS

Thanks for your interest in contributing to AgentOS. The project aims to make multi-agent AI workflows useful in the terminal while remaining portable across Linux and Windows.

> **Current status:** This is a starter contribution guide for the planned repository. Confirm the commands and policies against the implementation as it evolves.

## Before you start

1. Read the project [README](README.md), [MVP scope](docs/MVP_SCOPE.md), and [repository structure](docs/REPOSITORY_STRUCTURE.md).
2. Search existing issues and pull requests before opening a duplicate.
3. For a large change, open an issue first to agree on scope and design.
4. Never include API keys, personal data, private source code, or other secrets in issues, logs, fixtures, or commits.

## Development setup

The project is planned for Python 3.11+; the exact supported versions will be confirmed in `pyproject.toml`.

```bash
git clone <your-fork-url>
cd agentos
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Activate the virtual environment using the instructions for your shell. The editable install command becomes valid once packaging metadata and development dependencies are implemented.

## Cross-platform expectations

- Test on Linux and Windows whenever possible.
- Use `pathlib` rather than hardcoded path separators.
- Avoid assuming Bash or POSIX-only utilities are available.
- Put OS-specific behavior behind interfaces in `src/agentos/platform/`.
- Prefer Python APIs over shell commands when the same operation can be performed safely in-process.
- If shell execution is necessary, use argument lists, a working-directory boundary, timeouts, output limits, and explicit user approval.
- Do not make `tmux` or PowerShell a mandatory dependency of the core.

## Code guidelines

- Keep functions small and responsibilities clear.
- Add type annotations to public interfaces.
- Use docstrings for public modules and non-obvious behavior.
- Keep provider-specific details inside provider adapters.
- Keep agent instructions, tool permissions, and expected output schemas explicit.
- Handle cancellation, provider errors, timeouts, and malformed model output.
- Avoid logging secrets, full environment variables, or sensitive file contents.
- Prefer deterministic tests with mocked providers; mark tests requiring a live model or external service.
- Do not add dependencies without explaining why they are needed.

## Tests and quality checks

The exact commands will be finalized with the first implementation. The intended baseline is:

```bash
python -m pytest
ruff check .
ruff format --check .
```

If a type checker is adopted, its check should be included in CI and documented here. Run the full test suite on both Linux and Windows before merging platform-sensitive changes.

Tests should cover, where relevant:

- Normal behavior and error cases.
- Windows and Linux path differences.
- Process timeout, cancellation, and non-zero exit codes.
- Provider timeouts, rate limits, malformed responses, and retries.
- Tool permission denials and approval flows.
- Redaction of secrets from logs.
- Agent handoff limits and orchestrator failure handling.

## Pull request process

1. Create a focused branch from the default branch.
2. Make a small, reviewable change.
3. Add or update tests and documentation.
4. Run the available checks locally.
5. Open a pull request using the repository template.
6. Explain the problem, the solution, how it was tested, and any platform limitations.
7. Call out changes to configuration, permissions, dependencies, or public interfaces.

A PR should not be merged if it breaks supported-platform CI, weakens approval boundaries without review, or introduces unredacted secrets.

## Commit messages

Use clear, imperative messages. A lightweight convention is encouraged:

- `feat: add provider interface`
- `fix: handle Windows config paths`
- `test: cover command timeout behavior`
- `docs: clarify agent permission model`
- `refactor: isolate process adapter`

Conventional Commits are a suggested convention, not a hard requirement unless the maintainers later adopt it formally.

## Issues and bug reports

Include:

- A concise title and expected behavior.
- OS and version (Linux distribution or Windows version).
- Python version and installation method.
- Minimal reproduction steps.
- Relevant logs with secrets and personal data removed.
- Whether the issue reproduces on both supported platforms.

For provider bugs, include the provider type and a sanitized error response, never an API key.

## Security issues

Do not publish exploitable vulnerabilities or secrets in a public issue. Until a private security reporting channel is configured, contact the maintainers through a private channel listed in the repository profile. Do not claim a formal security response SLA unless one has been established.

## Scope and compatibility

The first MVP prioritizes Linux and Windows, with macOS considered later. New features should not introduce a platform-specific dependency into the core without a documented reason and a graceful fallback.

## License

By submitting a contribution, you agree that it may be distributed under the project’s MIT License. Ensure you have the right to contribute the code and that any copied material is compatible with the project license.
