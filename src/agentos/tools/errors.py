"""Dedicated exceptions raised by the tool execution gate."""


class ToolError(Exception):
    """Base class for every tool dispatch failure."""


class UnknownToolError(ToolError):
    """Raised when a requested tool is not registered."""


class ToolApprovalRequiredError(ToolError):
    """Raised when a tool requires approval that has not been granted."""


class ToolArgumentsError(ToolError):
    """Raised when arguments are not an object or violate the declared schema."""


class ToolExecutionError(ToolError):
    """Raised when a tool fails internally or returns an invalid result."""
