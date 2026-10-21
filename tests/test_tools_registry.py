"""Tests for AgentOS tool contracts and the allowlisted registry."""

from collections.abc import Mapping
from pathlib import Path

import pytest

from agentos.tools import (
    ToolContext,
    ToolDefinition,
    ToolRegistry,
    ToolResult,
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
) -> ToolDefinition:
    """Build a valid tool definition with overridable fields."""
    return ToolDefinition(
        name=name,
        description=description,
        parameters_schema=(parameters_schema if parameters_schema is not None else sample_schema()),
    )


class FakeTool:
    """Minimal Tool implementation used by registry tests."""

    def __init__(self, definition: ToolDefinition) -> None:
        self._definition = definition

    @property
    def definition(self) -> ToolDefinition:
        return self._definition

    async def execute(
        self,
        arguments: Mapping[str, object],
        context: ToolContext,
    ) -> ToolResult:
        return ToolResult(content=f"processed {sorted(arguments)}")


def test_valid_tool_metadata_is_accepted() -> None:
    name = "a" + "_" * 63
    definition = make_definition(name=name)

    assert definition.name == name
    assert definition.description == "Read a file from the workspace."
    assert definition.parameters_schema == sample_schema()


@pytest.mark.parametrize(
    "name",
    [
        "",
        "Read_File",
        "read-file",
        "1st_file",
        "read file",
        "_internal",
        "a" * 65,
        "Tool",
    ],
)
def test_invalid_tool_names_are_rejected(name: object) -> None:
    with pytest.raises(ValueError, match="Tool name"):
        make_definition(name=name)


@pytest.mark.parametrize("description", ["", "   ", 42])
def test_blank_descriptions_are_rejected(description: object) -> None:
    with pytest.raises(ValueError, match="description"):
        make_definition(description=description)


@pytest.mark.parametrize(
    "schema",
    [
        "not a mapping",
        [],
        {"properties": {}, "additionalProperties": False},
        {"type": "array", "properties": {}, "additionalProperties": False},
        {"type": "object", "additionalProperties": False},
        {"type": "object", "properties": [], "additionalProperties": False},
        {
            "type": "object",
            "properties": {},
            "required": "path",
            "additionalProperties": False,
        },
        {
            "type": "object",
            "properties": {},
            "required": [""],
            "additionalProperties": False,
        },
    ],
)
def test_invalid_schema_envelopes_are_rejected(schema: object) -> None:
    with pytest.raises(ValueError, match="parameters_schema"):
        make_definition(parameters_schema=schema)


@pytest.mark.parametrize(
    "additional_properties",
    [
        True,
        "false",
        0,
        None,
    ],
)
def test_permissive_additional_properties_are_rejected(
    additional_properties: object,
) -> None:
    schema: dict[str, object] = {
        "type": "object",
        "properties": {},
        "additionalProperties": additional_properties,
    }

    with pytest.raises(ValueError, match="additionalProperties"):
        make_definition(parameters_schema=schema)


def test_missing_additional_properties_is_rejected() -> None:
    schema: dict[str, object] = {
        "type": "object",
        "properties": {},
    }

    with pytest.raises(ValueError, match="additionalProperties"):
        make_definition(parameters_schema=schema)


@pytest.mark.parametrize("flag", ["yes", 1, None])
def test_invalid_approval_flag_is_rejected(flag: object) -> None:
    with pytest.raises(ValueError, match="approval_required"):
        ToolDefinition(
            name="noop",
            description="Do nothing.",
            parameters_schema=sample_schema(),
            approval_required=flag,
        )


def test_approval_required_defaults_to_true() -> None:
    assert make_definition().approval_required is True

    explicit = ToolDefinition(
        name="noop",
        description="Do nothing.",
        parameters_schema=sample_schema(),
        approval_required=False,
    )
    assert explicit.approval_required is False


def test_tool_is_registered_and_retrieved() -> None:
    registry = ToolRegistry()
    tool = FakeTool(make_definition())

    registry.register(tool)

    assert registry.get("read_file") is tool


def test_duplicate_registration_fails_clearly() -> None:
    registry = ToolRegistry()
    registry.register(FakeTool(make_definition()))

    with pytest.raises(ValueError, match="already registered"):
        registry.register(FakeTool(make_definition()))


def test_unknown_tool_lookup_returns_none() -> None:
    registry = ToolRegistry()
    registry.register(FakeTool(make_definition()))

    assert registry.get("missing_tool") is None
    assert ToolRegistry().get("read_file") is None


def test_definitions_preserve_registration_order_as_tuple() -> None:
    registry = ToolRegistry()
    registry.register(FakeTool(make_definition(name="alpha_tool")))
    registry.register(FakeTool(make_definition(name="beta_tool")))
    registry.register(FakeTool(make_definition(name="gamma_tool")))

    definitions = registry.list_definitions()

    assert isinstance(definitions, tuple)
    assert [definition.name for definition in definitions] == [
        "alpha_tool",
        "beta_tool",
        "gamma_tool",
    ]


def test_non_tool_registration_is_rejected() -> None:
    registry = ToolRegistry()

    with pytest.raises(TypeError, match="ToolDefinition"):
        registry.register(object())


def test_tool_result_represents_output_and_error() -> None:
    success = ToolResult(content="all good")

    assert success.content == "all good"
    assert success.is_error is False

    failure = ToolResult(content="permission denied", is_error=True)

    assert failure.content == "permission denied"
    assert failure.is_error is True


@pytest.mark.parametrize(
    "kwargs",
    [
        {"content": 42},
        {"content": None},
        {"content": "ok", "is_error": "yes"},
        {"content": "ok", "is_error": 1},
    ],
)
def test_tool_result_rejects_invalid_fields(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        ToolResult(**kwargs)


def test_tool_context_accepts_valid_limits(tmp_path: Path) -> None:
    context = ToolContext(workspace=tmp_path, max_output_chars=20_000)

    assert context.workspace == tmp_path
    assert context.max_output_chars == 20_000

    expanded = ToolContext(workspace="~/agentos-tools", max_output_chars=1_024)
    assert expanded.workspace == Path("~/agentos-tools").expanduser()


@pytest.mark.parametrize("value", [0, 1_023, 100_001, True, "20000"])
def test_tool_context_rejects_invalid_output_limits(
    tmp_path: Path,
    value: object,
) -> None:
    with pytest.raises(ValueError, match="max_output_chars"):
        ToolContext(workspace=tmp_path, max_output_chars=value)
