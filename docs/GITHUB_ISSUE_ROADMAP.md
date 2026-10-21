# GitHub Issue Roadmap

This roadmap is a suggested initial issue backlog. Create issues in GitHub after the repository exists; this document does not create them.

Labels to establish:

- `type:feature`, `type:bug`, `type:docs`, `type:security`, `type:maintenance`
- `area:core`, `area:cli`, `area:tui`, `area:providers`, `area:tools`, `area:platform`, `area:ci`
- `platform:windows`, `platform:linux`, `good first issue`, `help wanted`
- `priority:P0`, `priority:P1`, `priority:P2`

## Milestone 0 — Project foundation

### AGENTOS-001 — Establish package metadata and CLI entry point
**Priority:** P0 · **Labels:** `type:feature`, `area:cli`

**Description:** Create `pyproject.toml`, package skeleton under `src/agentos/`, and an `agentos` command with `--help` and `--version`.

**Acceptance criteria**
- Editable installation succeeds in a clean virtual environment on Windows and Linux.
- `agentos --help` and `agentos --version` work.
- Package imports do not require provider credentials.
- Supported Python versions are explicitly declared.

### AGENTOS-002 — Add Linux and Windows CI matrix
**Priority:** P0 · **Labels:** `type:maintenance`, `area:ci`, `platform:windows`, `platform:linux`

**Description:** Configure GitHub Actions to install the package and run tests on both operating systems for pull requests and pushes.

**Acceptance criteria**
- At least one supported Python version runs on Ubuntu and Windows runners.
- Failures block required checks when branch protection is configured.
- CI logs avoid printing secrets.
- Developer documentation explains how to run the same checks locally.

### AGENTOS-003 — Add lint, formatting, and test baseline
**Priority:** P0 · **Labels:** `type:maintenance`, `area:ci`

**Acceptance criteria**
- pytest and Ruff (or explicitly selected alternatives) are configured.
- A small smoke test verifies import and CLI startup.
- CI runs quality checks on both platforms.

### AGENTOS-004 — Add MIT license and contribution policy
**Priority:** P0 · **Labels:** `type:docs`

**Acceptance criteria**
- Full MIT license text is present.
- `CONTRIBUTING.md`, Code of Conduct, and PR template exist.
- Repository status and planned features are accurately described.

## Milestone 1 — Configuration and single-agent loop

### AGENTOS-010 — Implement validated TOML configuration
**Priority:** P0 · **Labels:** `type:feature`, `area:core`

**Acceptance criteria**
- Config supports default provider/model, agent settings, workspace, and runtime limits.
- Precedence is CLI > environment > file > defaults.
- Invalid values produce actionable errors.
- Example config contains no real secrets.

### AGENTOS-011 — Define provider interface and normalized response types
**Priority:** P0 · **Labels:** `type:feature`, `area:providers`, `area:core`

**Acceptance criteria**
- Provider requests and responses are represented by core-owned types.
- Timeout, cancellation, and provider errors have documented semantics.
- Provider SDK types do not leak into orchestration APIs.
- Tests use a fake provider.

### AGENTOS-012 — Implement first provider adapter
**Priority:** P0 · **Labels:** `type:feature`, `area:providers`

**Description:** Select and implement one provider for the first end-to-end loop. Keep the choice configurable and behind the interface.

**Acceptance criteria**
- Credentials are read from environment variables or a secure user configuration path.
- Missing credentials produce a helpful error.
- Timeout and authentication errors are normalized.
- Tests mock network responses; live-provider tests are opt-in.

### AGENTOS-013 — Add agent profile and registry interfaces
**Priority:** P0 · **Labels:** `type:feature`, `area:core`

**Acceptance criteria**
- Built-in `architect`, `coder`, `researcher`, and `reviewer` profiles are available.
- Each profile declares its allowed tools and output expectations.
- A user can invoke one agent directly.
- Agent profiles are independent of provider-specific SDKs.

### AGENTOS-014 — Add basic CLI ask command
**Priority:** P0 · **Labels:** `type:feature`, `area:cli`

**Acceptance criteria**
- `agentos ask "..."` invokes the configured default agent.
- `--agent` and model/provider overrides are validated.
- Output includes agent identity and clear error reporting.
- No shell or filesystem write tool is invoked by this command.

## Milestone 2 — Safe workspace tools

### AGENTOS-020 — Implement workspace-confined read-only filesystem tools
**Priority:** P0 · **Labels:** `type:feature`, `area:tools`, `area:security`

**Acceptance criteria**
- List and read operations are restricted to a configured workspace.
- Path traversal and symlink edge cases are considered and tested.
- Output size limits are enforced.
- No write capability is exposed through the read-only interface.

### AGENTOS-021 — Implement permission and approval interfaces
**Priority:** P0 · **Labels:** `type:feature`, `area:security`

**Acceptance criteria**
- Tools declare required permissions.
- Write and process actions require explicit approval.
- Denied actions cannot run.
- Approval and denial decisions produce redacted audit events.

### AGENTOS-022 — Add controlled process runner
**Priority:** P1 · **Labels:** `type:feature`, `area:tools`, `area:platform`

**Acceptance criteria**
- Uses argument lists rather than interpolated shell strings by default.
- Requires explicit approval and uses an allowlist in the MVP.
- Has a working-directory boundary, timeout, output limit, and exit-code capture.
- Cancellation and process cleanup are tested on Windows and Linux.

### AGENTOS-023 — Add proposed-diff workflow for file changes
**Priority:** P1 · **Labels:** `type:feature`, `area:tools`, `area:security`

**Acceptance criteria**
- Proposed edits can be previewed before application.
- User approval is required before writing.
- Failed writes do not leave partial files where avoidable.
- Tests cover denied approval and write errors.

## Milestone 3 — Orchestration

### AGENTOS-030 — Define task, plan, result, and status models
**Priority:** P0 · **Labels:** `type:feature`, `area:core`

**Acceptance criteria**
- Task and result models are typed and serializable.
- Status includes pending, running, waiting for approval, completed, failed, and cancelled.
- Invalid state transitions are rejected or explicitly handled.

### AGENTOS-031 — Implement bounded task planner
**Priority:** P1 · **Labels:** `type:feature`, `area:core`

**Acceptance criteria**
- Planner emits a structured plan with a bounded number of steps.
- Plan is shown before side-effecting execution.
- Invalid plan output is handled safely.
- Limits are configurable and have safe defaults.

### AGENTOS-032 — Implement router and bounded agent handoffs
**Priority:** P1 · **Labels:** `type:feature`, `area:core`

**Acceptance criteria**
- Direct agent selection remains available.
- Router can suggest or select an agent with a short rationale.
- Handoffs pass structured, minimal context.
- Maximum steps, concurrency, elapsed time, and tool calls are enforced.

### AGENTOS-033 — Implement reviewer and final synthesis
**Priority:** P1 · **Labels:** `type:feature`, `area:core`

**Acceptance criteria**
- Reviewer receives plan/output/diff as appropriate, not unrestricted session state.
- Findings include evidence and severity where possible.
- Final response distinguishes performed actions from recommendations.
- Reviewer feedback does not automatically authorize more actions.

### AGENTOS-034 — Add cancellation and execution budget handling
**Priority:** P1 · **Labels:** `type:feature`, `area:core`

**Acceptance criteria**
- User can cancel a running task.
- Provider requests and child processes are cancelled or stopped where supported.
- Step/time/concurrency limits stop runaway loops.
- Cancellation is reflected in session status.

## Milestone 4 — Sessions and terminal experience

### AGENTOS-040 — Add structured logging and secret redaction
**Priority:** P0 · **Labels:** `type:feature`, `area:security`

**Acceptance criteria**
- Logs include task IDs and agent labels.
- API keys and configured secret values are redacted.
- Output size limits prevent runaway logs.
- Tests verify redaction behavior.

### AGENTOS-041 — Add SQLite session storage
**Priority:** P2 · **Labels:** `type:feature`, `area:core`

**Acceptance criteria**
- Tasks and summary metadata persist locally.
- Storage schema has a versioning/migration strategy.
- Stored records avoid secrets by default.
- User can list and inspect recent sessions.

### AGENTOS-042 — Add minimal Textual TUI
**Priority:** P2 · **Labels:** `type:feature`, `area:tui`

**Acceptance criteria**
- Shows current task, agent status, recent events, and approval prompts.
- Supports cancellation.
- Core CLI remains usable without launching the TUI.
- Basic navigation is tested on Windows and Linux terminals.

### AGENTOS-043 — Add sessions and config commands
**Priority:** P2 · **Labels:** `type:feature`, `area:cli`

**Acceptance criteria**
- `agentos sessions` lists recent local sessions.
- `agentos config` reports active config sources without revealing secrets.
- Missing or corrupt storage produces a recoverable error.

## Milestone 5 — MVP release hardening

### AGENTOS-050 — Add cross-platform integration test coverage
**Priority:** P0 · **Labels:** `type:maintenance`, `area:ci`, `platform:windows`, `platform:linux`

**Acceptance criteria**
- Tests cover path handling, config, CLI startup, process behavior, and cancellation.
- Windows and Linux CI pass.
- OS-specific skips include a clear reason.
- No core feature silently assumes POSIX behavior.

### AGENTOS-051 — Document install, config, permissions, and troubleshooting
**Priority:** P0 · **Labels:** `type:docs`

**Acceptance criteria**
- Fresh setup documented for Windows and Linux.
- Example config and environment variables documented.
- Tool permission behavior is explained clearly.
- Troubleshooting covers common provider and shell errors.

### AGENTOS-052 — Perform MVP security review
**Priority:** P0 · **Labels:** `type:security`

**Acceptance criteria**
- Threat model and tool permission boundaries are reviewed.
- Arbitrary model-generated shell execution is not enabled by default.
- Workspace path checks and secret redaction are tested.
- Known limitations are documented before release.

### AGENTOS-053 — Prepare pre-release checklist and versioning
**Priority:** P1 · **Labels:** `type:maintenance`

**Acceptance criteria**
- Package build can be created reproducibly.
- Version and changelog conventions are documented.
- README status matches the shipped behavior.
- Linux and Windows installation smoke tests pass.

## Suggested order

Build in this sequence:

1. AGENTOS-001 to AGENTOS-004
2. AGENTOS-010 to AGENTOS-014
3. AGENTOS-020 and AGENTOS-021
4. AGENTOS-030, AGENTOS-031, AGENTOS-032
5. AGENTOS-040 and AGENTOS-050
6. Add the TUI, sessions, and richer tools only after the CLI loop is reliable.

The issue IDs are local planning identifiers, not actual GitHub issue numbers.
