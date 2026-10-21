"""Tests for the centralized tool execution gate."""

import asyncio
from collections.abc import Mapping
from pathlib import Path

import pytest

from agentos.tools import (
    ToolApprovalRequiredError,
    ToolArgumentsError,
    ToolContext,
    ToolDefinition,
    ToolDispatcher,
    ToolExecutionError,
    ToolRegistry,
    ToolResult,
    UnknownToolError,
)


def sample_schema() -> dict[str, object]:
    """Return a valid JSON Schema-style envelope."""
    return {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
        "additionalProperties": False,
    }


def make_definition(
    name: str = "read_file",
    description: str = "Read a file from the workspace.",
    parameters_schema: Mapping[str, object] | None = None,
    *,
    approval_required: bool = False,
) -> ToolDefinition:
    """Build a valid tool definition with overridable fields."""
    return ToolDefinition(
        name=name,
        description=description,
        parameters_schema=(parameters_schema if parameters_schema is not None else sample_schema()),
        approval_required=approval_required,
    )


class RecordingTool:
    """Fake tool that records every execution and returns a fixed outcome."""

    def __init__(
        self,
        definition: ToolDefinition,
        *,
        result: ToolResult | None = None,
        error: Exception | None = None,
        raw_return: object | None = None,
    ) -> None:
        self._definition = definition
        self._result = result
        self._error = error
        self._raw_return = raw_return
        self.calls: list[tuple[Mapping[str, object], ToolContext]] = []

    @property
    def definition(self) -> ToolDefinition:
        return self._definition

    async def execute(
        self,
        arguments: Mapping[str, object],
        context: ToolContext,
    ) -> ToolResult:
        self.calls.append((arguments, context))
        if self._error is not None:
            raise self._error
        if self._raw_return is not None:
            return self._raw_return
        return self._result if self._result is not None else ToolResult(content="ok")


def build_dispatcher(*tools: RecordingTool) -> ToolDispatcher:
    registry = ToolRegistry()
    for tool in tools:
        registry.register(tool)
    return ToolDispatcher(registry)


def host_context(tmp_path: Path) -> ToolContext:
    return ToolContext(workspace=tmp_path, max_output_chars=20_000)


def run_tool(
    dispatcher: ToolDispatcher,
    arguments: object,
    context: ToolContext,
    *,
    name: str = "read_file",
    approval_granted: object = False,
) -> ToolResult:
    return asyncio.run(
        dispatcher.execute(
            name,
            arguments,
            context,
            approval_granted=approval_granted,
        )
    )


def test_valid_arguments_reach_registered_tool(tmp_path: Path) -> None:
    tool = RecordingTool(make_definition())
    dispatcher = build_dispatcher(tool)
    context = host_context(tmp_path)

    result = run_tool(dispatcher, {"path": "notes.txt"}, context)

    assert result.content == "ok"
    assert result.is_error is False
    assert len(tool.calls) == 1
    recorded_arguments, recorded_context = tool.calls[0]
    assert recorded_arguments == {"path": "notes.txt"}
    assert recorded_context is context


def test_required_tool_without_approval_is_rejected(tmp_path: Path) -> None:
    tool = RecordingTool(make_definition(approval_required=True))
    dispatcher = build_dispatcher(tool)
    context = host_context(tmp_path)

    with pytest.raises(ToolApprovalRequiredError, match="requires approval"):
        run_tool(dispatcher, {"path": "notes.txt"}, context)

    assert tool.calls == []


def test_explicit_host_approval_allows_execution(tmp_path: Path) -> None:
    tool = RecordingTool(make_definition(approval_required=True))
    dispatcher = build_dispatcher(tool)
    context = host_context(tmp_path)

    result = run_tool(dispatcher, {"path": "notes.txt"}, context, approval_granted=True)

    assert result.content == "ok"
    assert len(tool.calls) == 1


def test_tool_not_requiring_approval_runs_without_grant(tmp_path: Path) -> None:
    tool = RecordingTool(make_definition(approval_required=False))
    dispatcher = build_dispatcher(tool)
    context = host_context(tmp_path)

    result = run_tool(dispatcher, {"path": "notes.txt"}, context)

    assert result.content == "ok"
    assert len(tool.calls) == 1


def test_unknown_tool_is_rejected(tmp_path: Path) -> None:
    registered = RecordingTool(make_definition())
    dispatcher = build_dispatcher(registered)
    context = host_context(tmp_path)

    with pytest.raises(UnknownToolError, match="ghost_tool"):
        run_tool(dispatcher, {"path": "x"}, context, name="ghost_tool")

    assert registered.calls == []


def test_malformed_arguments_are_rejected(tmp_path: Path) -> None:
    tool = RecordingTool(make_definition())
    dispatcher = build_dispatcher(tool)
    context = host_context(tmp_path)

    for arguments in ["not-an-object", None, 42, ["path"]]:
        with pytest.raises(ToolArgumentsError, match="expected a JSON object"):
            run_tool(dispatcher, arguments, context)

    assert tool.calls == []


def test_schema_invalid_arguments_are_rejected(tmp_path: Path) -> None:
    tool = RecordingTool(make_definition())
    dispatcher = build_dispatcher(tool)
    context = host_context(tmp_path)

    with pytest.raises(ToolArgumentsError, match="required property"):
        run_tool(dispatcher, {}, context)
    with pytest.raises(ToolArgumentsError, match="not of type"):
        run_tool(dispatcher, {"path": 5}, context)
    with pytest.raises(ToolArgumentsError, match="Additional properties"):
        run_tool(dispatcher, {"path": "a.txt", "extra": 1}, context)

    assert tool.calls == []


def test_rejected_calls_never_reach_execute(tmp_path: Path) -> None:
    tool = RecordingTool(make_definition(approval_required=True))
    dispatcher = build_dispatcher(tool)
    context = host_context(tmp_path)

    with pytest.raises(ToolApprovalRequiredError):
        run_tool(dispatcher, {"path": "a.txt"}, context)
    with pytest.raises(UnknownToolError):
        run_tool(dispatcher, {"path": "a.txt"}, context, name="missing_tool")
    with pytest.raises(TypeError):
        run_tool(dispatcher, {"path": "a.txt"}, context, approval_granted="yes")
    with pytest.raises(ToolArgumentsError):
        run_tool(dispatcher, {}, context, approval_granted=True)

    assert tool.calls == []


@pytest.mark.parametrize("value", ["true", 1, 0, None, "yes"])
def test_invalid_approval_values_are_rejected(tmp_path: Path, value: object) -> None:
    tool = RecordingTool(make_definition())
    dispatcher = build_dispatcher(tool)
    context = host_context(tmp_path)

    with pytest.raises(TypeError, match="approval_granted must be a boolean"):
        run_tool(dispatcher, {"path": "a.txt"}, context, approval_granted=value)

    assert tool.calls == []


def test_tool_exception_is_wrapped_safely(tmp_path: Path) -> None:
    tool = RecordingTool(make_definition(), error=RuntimeError("secret internal text"))
    dispatcher = build_dispatcher(tool)
    context = host_context(tmp_path)

    with pytest.raises(ToolExecutionError, match="read_file") as excinfo:
        run_tool(dispatcher, {"path": "a.txt"}, context)

    message = str(excinfo.value)
    assert "secret internal text" not in message
    assert isinstance(excinfo.value.__cause__, RuntimeError)
    assert str(excinfo.value.__cause__) == "secret internal text"
    assert len(tool.calls) == 1


@pytest.mark.parametrize("raw_return", [{"content": "oops"}, "done", 42])
def test_invalid_return_type_is_rejected(tmp_path: Path, raw_return: object) -> None:
    tool = RecordingTool(make_definition(), raw_return=raw_return)
    dispatcher = build_dispatcher(tool)
    context = host_context(tmp_path)

    with pytest.raises(ToolExecutionError, match="invalid result"):
        run_tool(dispatcher, {"path": "a.txt"}, context)

    assert len(tool.calls) == 1


def test_schema_mutation_cannot_bypass_validation(tmp_path: Path) -> None:
    schema = sample_schema()
    definition = make_definition(parameters_schema=schema)
    tool = RecordingTool(definition)
    dispatcher = build_dispatcher(tool)
    context = host_context(tmp_path)

    schema["properties"]["path"] = {"type": "number"}
    schema["additionalProperties"] = True
    schema["required"] = []

    with pytest.raises(TypeError):
        definition.parameters_schema["additionalProperties"] = True
    with pytest.raises(TypeError):
        definition.parameters_schema["properties"]["path"] = {"type": "number"}

    with pytest.raises(ToolArgumentsError):
        run_tool(dispatcher, {"path": 5, "extra": 1}, context)

    assert tool.calls == []
    assert definition.parameters_schema["additionalProperties"] is False

    result = run_tool(dispatcher, {"path": "a.txt"}, context)

    assert result.content == "ok"
    assert len(tool.calls) == 1


def test_host_context_is_passed_exactly(tmp_path: Path) -> None:
    workspace = tmp_path / "host-workspace"
    context = ToolContext(workspace=workspace, max_output_chars=50_000)
    schema = {
        "type": "object",
        "properties": {"workspace": {"type": "string"}},
        "required": ["workspace"],
        "additionalProperties": False,
    }
    tool = RecordingTool(make_definition(parameters_schema=schema))
    dispatcher = build_dispatcher(tool)

    run_tool(dispatcher, {"workspace": "/tmp/model-owned"}, context)

    recorded_arguments, recorded_context = tool.calls[0]
    assert recorded_arguments == {"workspace": "/tmp/model-owned"}
    assert recorded_context is context
    assert recorded_context.workspace == workspace
    assert recorded_context.max_output_chars == 50_000
