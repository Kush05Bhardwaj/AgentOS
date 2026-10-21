"""Centralized validation and approval gate for tool execution."""

from collections.abc import Mapping

from jsonschema import Draft202012Validator
from jsonschema.exceptions import best_match

from agentos.tools.base import ToolContext, ToolDefinition, ToolResult
from agentos.tools.errors import (
    ToolApprovalRequiredError,
    ToolArgumentsError,
    ToolExecutionError,
    UnknownToolError,
)
from agentos.tools.registry import ToolRegistry


class ToolDispatcher:
    """Runs every tool call through a deterministic execution gate.

    AgentOS, never the model, decides whether a tool exists, whether
    its arguments are valid, and whether execution is permitted. The
    dispatcher is backed by an explicitly supplied allowlist registry
    and never discovers or imports tools on its own.
    """

    def __init__(self, registry: ToolRegistry) -> None:
        """Create a dispatcher backed by an explicit tool allowlist."""
        self._registry = registry

    async def execute(
        self,
        name: str,
        arguments: Mapping[str, object],
        context: ToolContext,
        *,
        approval_granted: bool = False,
    ) -> ToolResult:
        """Resolve, approve, validate, and execute a single tool call.

        Raises:
            TypeError: If approval_granted is not a real boolean.
            UnknownToolError: If the tool is not registered.
            ToolApprovalRequiredError: If approval is required but missing.
            ToolArgumentsError: If arguments are not an object or violate
                the declared schema.
            ToolExecutionError: If the tool fails internally or returns
                an invalid result.
        """
        if type(approval_granted) is not bool:
            raise TypeError("approval_granted must be a boolean.")

        tool = self._registry.get(name)
        if tool is None:
            raise UnknownToolError(f"Tool '{name}' is not registered.")

        definition = tool.definition

        if definition.approval_required and not approval_granted:
            raise ToolApprovalRequiredError(f"Tool '{name}' requires approval before execution.")

        self._validate_arguments(name, definition, arguments)

        try:
            result = await tool.execute(arguments, context)
        except Exception as exc:
            raise ToolExecutionError(f"Tool '{name}' failed during execution.") from exc

        if not isinstance(result, ToolResult):
            raise ToolExecutionError(f"Tool '{name}' returned an invalid result.")

        return result

    @staticmethod
    def _validate_arguments(
        name: str,
        definition: ToolDefinition,
        arguments: Mapping[str, object],
    ) -> None:
        """Check model arguments against the definition's JSON Schema."""
        if not isinstance(arguments, Mapping):
            raise ToolArgumentsError(
                f"Invalid arguments for tool '{name}': expected a JSON object."
            )

        validator = Draft202012Validator(definition.parameters_schema)
        error = best_match(validator.iter_errors(dict(arguments)))

        if error is not None:
            raise ToolArgumentsError(
                f"Invalid arguments for tool '{name}': {error.message}"
            ) from error
