"""Tool contracts shared by every AgentOS tool implementation."""

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from agentos.config.defaults import (
    MAX_TOOL_OUTPUT_MAXIMUM,
    MAX_TOOL_OUTPUT_MINIMUM,
)

_NAME_PATTERN = re.compile(r"[a-z][a-z0-9_]{0,63}")


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    """Public metadata describing a tool and its argument contract.

    The parameters schema follows JSON Schema conventions so model
    providers can render it as tool/function declarations without
    adapter-specific translation.
    """

    name: str
    description: str
    parameters_schema: Mapping[str, object]
    approval_required: bool = True

    def __post_init__(self) -> None:
        """Validate the name, description, schema envelope, and policy flag."""
        if not isinstance(self.name, str) or _NAME_PATTERN.fullmatch(self.name) is None:
            raise ValueError("Tool name must match [a-z][a-z0-9_]{0,63}.")

        if not isinstance(self.description, str) or not self.description.strip():
            raise ValueError("Tool description must be a non-empty string.")

        schema = self.parameters_schema

        if not isinstance(schema, Mapping):
            raise ValueError("parameters_schema must be a mapping.")

        if schema.get("type") != "object":
            raise ValueError('parameters_schema root must declare "type": "object".')

        properties = schema.get("properties")
        if not isinstance(properties, Mapping):
            raise ValueError('parameters_schema must declare a "properties" mapping.')

        required = schema.get("required")
        if required is not None and (
            not isinstance(required, Sequence)
            or isinstance(required, (str, bytes))
            or not all(isinstance(item, str) and item.strip() for item in required)
        ):
            raise ValueError('parameters_schema "required" must be a list of non-empty strings.')

        if schema.get("additionalProperties") is not False:
            raise ValueError('parameters_schema must declare "additionalProperties": false.')

        if type(self.approval_required) is not bool:
            raise ValueError("approval_required must be a boolean.")

        object.__setattr__(self, "parameters_schema", dict(schema))


@dataclass(frozen=True, slots=True)
class ToolResult:
    """Text output returned by a tool execution."""

    content: str
    is_error: bool = False

    def __post_init__(self) -> None:
        """Require textual content and a boolean error flag."""
        if not isinstance(self.content, str):
            raise ValueError("ToolResult.content must be a string.")

        if type(self.is_error) is not bool:
            raise ValueError("ToolResult.is_error must be a boolean.")


@dataclass(frozen=True, slots=True)
class ToolContext:
    """Trusted execution context supplied by the host application.

    This must be constructed by AgentOS itself, never populated from
    model-generated arguments.
    """

    workspace: Path
    max_output_chars: int

    def __post_init__(self) -> None:
        """Normalize the workspace and validate the output limit."""
        try:
            workspace = Path(self.workspace).expanduser()
        except (TypeError, ValueError) as exc:
            raise ValueError("workspace must be a valid filesystem path.") from exc

        object.__setattr__(self, "workspace", workspace)

        if type(self.max_output_chars) is not int or not (
            MAX_TOOL_OUTPUT_MINIMUM <= self.max_output_chars <= MAX_TOOL_OUTPUT_MAXIMUM
        ):
            raise ValueError(
                f"max_output_chars must be between {MAX_TOOL_OUTPUT_MINIMUM} "
                f"and {MAX_TOOL_OUTPUT_MAXIMUM}."
            )


class Tool(Protocol):
    """Contract that every tool implementation must follow."""

    @property
    def definition(self) -> ToolDefinition: ...

    async def execute(
        self,
        arguments: Mapping[str, object],
        context: ToolContext,
    ) -> ToolResult: ...
