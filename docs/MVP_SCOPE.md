# AgentOS MVP Scope

## Goal

Deliver a small but end-to-end multi-AI-agent terminal experience that is tested on **Linux and Windows from the first MVP**. The MVP should establish reliable interfaces and safety boundaries before adding broad autonomy.

## MVP success criteria

The MVP is successful when a new developer can:

1. Install AgentOS in a supported Python environment on Linux and Windows.
2. Configure a model provider without committing credentials.
3. invoke a single agent from the CLI and receive a useful response.
4. Ask AgentOS to route a task to an appropriate built-in agent.
5. Inspect a short plan and approve or reject tool actions.
6. Use read-only repository inspection and at least one controlled action tool.
7. Cancel a running task and receive a clear status.
8. See useful errors for provider failures, timeouts, invalid configuration, and permission denials.
9. Run automated tests locally and in CI on both operating systems.
10. Resume or inspect a locally stored session if session persistence is included in the first milestone.

## Must-have features

### 1. Packaging and command line

- Installable Python package with an `agentos` entry point.
- `agentos --help` and version output.
- Friendly error messages and non-zero exit codes for failures.
- CLI behavior that does not require a particular shell.

### 2. Configuration

- TOML configuration for default provider, model, agent profiles, tool permissions, and runtime limits.
- Environment variables for secrets and provider overrides.
- Clear precedence rules: command-line override > environment variable > config file > documented default.
- Validation at startup with actionable error messages.
- No credentials stored in source control or printed in logs.

### 3. Provider interface

- One concrete provider implemented end-to-end for the first usable milestone.
- A normalized request/response interface and streaming where supported.
- Explicit timeout and cancellation behavior.
- Consistent handling for authentication errors, rate limits, unavailable models, and malformed responses.
- Additional providers (such as Ollama and OpenAI-compatible endpoints) can be added behind the same interface.

### 4. Agent profiles

Initial built-in profiles:

- `architect`: break a task into a small plan and identify risks.
- `coder`: propose or implement a focused code change when authorized.
- `researcher`: summarize supplied context and, later, use approved research tools.
- `reviewer`: review a plan or diff and report issues with severity and evidence.

Each profile defines its role, allowed tools, expected output, and model override behavior. Role names are not guarantees of capability; results still need verification.

### 5. Routing and orchestration

- Direct invocation of a named agent.
- Basic task classification to suggest or select an agent.
- A bounded plan/execute/review flow for tasks that need more than one step.
- Structured handoff data instead of forwarding entire conversation histories indiscriminately.
- Limits on agent steps, tool calls, token usage where available, elapsed time, and concurrency.
- A final summary that distinguishes completed actions from suggestions.

### 6. Tool execution and permissions

- Read-only project tree listing and file reading, restricted to a configured workspace.
- A diff or proposed-change preview before writes.
- User approval before file modifications or shell command execution.
- Shell execution disabled by default or limited to an explicit allowlist during the earliest MVP.
- Process timeout, output truncation, exit-code capture, and cancellation handling.
- Audit events for tool requests, approvals, denials, and outcomes.
- No automatic execution of raw model-generated shell strings.

### 7. Cross-platform support

- Linux and Windows CI jobs run on every pull request.
- Tests for path normalization, configuration locations, CLI startup, process behavior, and cancellation.
- Platform-specific functionality isolated behind adapters.
- No required dependency on `tmux`, Bash, GNU utilities, or a Linux-only process API.
- Installation and troubleshooting documentation for both operating systems.

### 8. Observability

- Human-readable logs with a configurable verbosity.
- Task IDs and agent labels in output.
- Clear indication of current status, waiting for approval, failure, and cancellation.
- Secret redaction and output limits.

## Should-have, if the core is stable

- Small Textual TUI with agent status and recent events.
- SQLite-backed local session history.
- Streaming model output.
- Ollama adapter and an OpenAI-compatible provider adapter.
- Export of a task transcript with secrets redacted.

These should not delay a safe, testable CLI baseline.

## Explicitly out of scope for MVP

- Unattended autonomous operation over arbitrary repositories.
- Arbitrary shell access without approval.
- Distributed agents or remote worker infrastructure.
- Multi-user collaboration or hosted accounts.
- Browser automation and unrestricted web research.
- Vector database or complex semantic memory.
- Plugin marketplace.
- GUI desktop application.
- Guaranteed support for macOS before the Linux/Windows baseline is stable.
- Claims of sandboxing or security isolation without a verified implementation.

## Definition of done

A feature is done when:

- Acceptance criteria are documented and met.
- Tests cover success, failure, and permission-denied paths.
- Linux and Windows CI pass.
- Public interfaces and configuration are documented.
- Logs do not leak secrets.
- Destructive or external side effects are gated by permissions and approval.
- Known limitations are documented.
- The README does not advertise behavior that has not been implemented.

## Suggested first milestone

Ship a **single-agent CLI loop** with configuration, one provider, a read-only workspace tool, explicit approval scaffolding, and a Linux/Windows CI matrix. Add multi-agent orchestration only after the provider and tool interfaces are testable.
