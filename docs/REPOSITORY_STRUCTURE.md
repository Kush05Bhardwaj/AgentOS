# Proposed Repository Structure

This is a target structure, not a claim that these modules already exist. Start with the smallest runnable package and add directories as their interfaces become real.

```text
agentos/
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.yml
│   │   ├── feature_request.yml
│   │   └── config.yml
│   ├── workflows/
│   │   ├── tests.yml
│   │   └── lint.yml
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── FUNDING.yml                 # optional; omit until needed
├── docs/
│   ├── ARCHITECTURE.md
│   ├── MVP_SCOPE.md
│   ├── REPOSITORY_STRUCTURE.md
│   ├── GITHUB_ISSUE_ROADMAP.md
│   ├── CONFIGURATION.md
│   ├── SECURITY.md
│   └── DEVELOPMENT.md
├── examples/
│   ├── agentos.example.toml
│   └── custom_agent.example.toml
├── src/
│   └── agentos/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli/
│       │   ├── app.py              # command definitions and entry point
│       │   └── output.py           # consistent terminal formatting
│       ├── tui/
│       │   ├── app.py              # Textual app, added after CLI baseline
│       │   └── screens/            # optional TUI screens
│       ├── core/
│       │   ├── models.py           # Task, AgentResult, ToolCall, TaskStatus
│       │   ├── orchestrator.py     # bounded task execution
│       │   ├── router.py           # task-to-agent selection
│       │   ├── planner.py          # structured task plans
│       │   └── limits.py           # step/time/concurrency budgets
│       ├── agents/
│       │   ├── base.py             # agent contract
│       │   ├── registry.py         # built-in and configured profiles
│       │   └── profiles/           # architect, coder, researcher, reviewer
│       ├── providers/
│       │   ├── base.py             # normalized provider interface
│       │   ├── registry.py
│       │   └── adapters/           # concrete provider integrations
│       ├── tools/
│       │   ├── base.py             # typed tool contract
│       │   ├── registry.py
│       │   ├── filesystem.py       # workspace-confined read/write operations
│       │   ├── git.py              # read-only Git inspection first
│       │   └── process.py          # permission-gated process runner
│       ├── platform/
│       │   ├── base.py             # platform capabilities interface
│       │   ├── windows.py
│       │   └── linux.py
│       ├── config/
│       │   ├── loader.py
│       │   ├── schema.py
│       │   └── defaults.py
│       ├── memory/
│       │   ├── store.py            # session/task repository interface
│       │   └── sqlite_store.py
│       ├── security/
│       │   ├── approvals.py
│       │   ├── permissions.py
│       │   └── redaction.py
│       └── telemetry/
│           ├── logging.py
│           └── audit.py
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── cross_platform/
│   └── fixtures/
├── scripts/
│   └── dev_check.py                # optional local quality-check helper
├── .editorconfig
├── .gitattributes
├── .gitignore
├── .pre-commit-config.yaml          # optional
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── LICENSE
├── pyproject.toml
└── README.md
```

## Dependency direction

Prefer this direction:

- `cli/` and `tui/` call application services in `core/`.
- `core/` depends on interfaces for agents, providers, tools, storage, and approvals.
- Provider adapters implement `providers/base.py`.
- Tool implementations implement `tools/base.py` and request permissions through the security layer.
- Platform adapters isolate OS-specific behavior.
- `config/` creates validated settings objects; modules should not parse TOML independently.
- `memory/` persists explicit data models and should not contain orchestration policy.

Avoid circular imports. Keep model/provider SDK types from leaking into the core public interfaces.

## Cross-platform implementation notes

- Resolve config and data directories with a platform-aware library or documented platform rules.
- Use `pathlib.Path` and normalize workspace boundaries before file access.
- Do not assume path case sensitivity or symlink behavior is identical on all systems.
- Use `subprocess.run`/`Popen` with argument lists, timeouts, and explicit `cwd`; avoid `shell=True` by default.
- Treat PowerShell and POSIX shells as separate optional adapters rather than trying to translate arbitrary commands.
- Write process tests that assert behavior and exit status instead of matching shell-specific output.
- Test Windows-specific path cases and locked-file behavior.
- Keep `tmux` integration as an optional future adapter.

## Start small

The initial PR does not need every file in this tree. A practical first cut is `cli/`, `core/`, `providers/`, `config/`, `security/`, tests, packaging, and CI. Add `tui/`, SQLite storage, and extra adapters after the minimal loop works.
