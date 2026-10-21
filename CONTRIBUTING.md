# Contributing to AgentOS

Thanks for your interest in contributing to AgentOS. The project aims to make multi-agent AI workflows useful in the terminal while remaining portable across Linux and Windows.

The repository is in pre-alpha. Start with the [README](README.md), [MVP scope](docs/MVP_SCOPE.md), and [repository structure](docs/REPOSITORY_STRUCTURE.md). Features in the roadmap may not exist yet; please avoid assuming that planned capabilities are implemented.

## Before you start

1. Search existing issues and pull requests before opening a duplicate.
2. For a large change, open an issue first to agree on scope and design.
3. Never include API keys, personal data, private source code, or other secrets in issues, logs, fixtures, or commits.

## Development setup

AgentOS targets Python 3.11+. Follow [Development Setup](docs/DEVELOPMENT.md) for Windows and Linux commands.

The intended development dependencies are installed with:

    python -m pip install -e ".[dev]"

Activate the virtual environment using your shell's normal workflow, or invoke Python and AgentOS directly from the virtual environment.

## Cross-platform expectations

- Test on Linux and Windows whenever possible.
- Use pathlib rather than hardcoded path separators.
- Avoid assuming Bash or POSIX-only utilities are available.
- Put OS-specific behavior behind interfaces in src/agentos/platform/ as that layer is implemented.
- Prefer Python APIs over shell commands when the same operation can be performed safely in-process.
- If shell execution is necessary, use argument lists, a working-directory boundary, timeouts, output limits, and explicit user approval.
- Do not make tmux or PowerShell a mandatory dependency of the core.

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

Run the following from the project virtual environment:

    python -m pytest
    ruff check .
    ruff format --check .

Run the full test suite on both Linux and Windows before merging platform-sensitive changes.

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

Clear, imperative messages are encouraged. Examples:

- feat: add provider interface
- fix: handle Windows config paths
- test: cover command timeout behavior
- docs: clarify agent permission model
- refactor: isolate process adapter

## Issues and bug reports

Include the expected behavior, OS and version, Python version, minimal reproduction steps, sanitized logs, and whether the issue reproduces on both supported platforms. Never include API keys or private source code.

## Security issues

Do not publish exploitable vulnerabilities or secrets in a public issue. A private reporting channel still needs to be configured by maintainers; until then, do not post sensitive exploit details in public discussions.

## Scope and compatibility

The first MVP prioritizes Linux and Windows, with macOS considered later. New features should not introduce a platform-specific dependency into the core without a documented reason and a graceful fallback.

## License

By submitting a contribution, you agree that it may be distributed under the project's MIT License. Ensure you have the right to contribute the code and that any copied material is compatible with the project license.
