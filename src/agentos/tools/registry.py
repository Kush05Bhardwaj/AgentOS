"""Allowlisted registry of tool implementations."""

from agentos.tools.base import Tool, ToolDefinition


class ToolRegistry:
    """Deterministic allowlist mapping tool names to implementations.

    The registry only records what is permitted. It never discovers or
    loads tools from directories, configuration, or untrusted input,
    and it does not execute anything itself.
    """

    def __init__(self) -> None:
        """Create an empty registry."""
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool under its declared name.

        Raises:
            TypeError: If the tool provides no valid ToolDefinition.
            ValueError: If a tool with that name is already registered.
        """
        definition = getattr(tool, "definition", None)

        if not isinstance(definition, ToolDefinition):
            raise TypeError("Cannot register a tool without a valid ToolDefinition.")

        name = definition.name

        if name in self._tools:
            raise ValueError(f"Tool '{name}' is already registered.")

        self._tools[name] = tool

    def get(self, name: str) -> Tool | None:
        """Return the registered tool, or None when it is not allowlisted."""
        return self._tools.get(name)

    def list_definitions(self) -> tuple[ToolDefinition, ...]:
        """Return registered definitions in registration order."""
        return tuple(tool.definition for tool in self._tools.values())
