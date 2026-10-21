"""Tool contracts, the allowlisted registry, and the execution gate."""

from agentos.tools.base import (
    Tool,
    ToolContext,
    ToolDefinition,
    ToolResult,
)
from agentos.tools.dispatcher import ToolDispatcher
from agentos.tools.errors import (
    ToolApprovalRequiredError,
    ToolArgumentsError,
    ToolError,
    ToolExecutionError,
    UnknownToolError,
)
from agentos.tools.registry import ToolRegistry

__all__ = [
    "Tool",
    "ToolApprovalRequiredError",
    "ToolArgumentsError",
    "ToolContext",
    "ToolDefinition",
    "ToolDispatcher",
    "ToolError",
    "ToolExecutionError",
    "ToolRegistry",
    "ToolResult",
    "UnknownToolError",
]
