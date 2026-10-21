"""Static registry for the initial built-in agent profiles.

These profiles are metadata only at this stage; they do not call models or execute tools.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AgentProfile:
    """Describe a specialized agent role."""

    name: str
    summary: str


_BUILT_IN_AGENTS: tuple[AgentProfile, ...] = (
    AgentProfile(
        name="architect",
        summary="Break a task into steps and identify design trade-offs.",
    ),
    AgentProfile(
        name="coder",
        summary="Help implement focused code changes when execution is available.",
    ),
    AgentProfile(
        name="researcher",
        summary="Analyze supplied context and organize research questions.",
    ),
    AgentProfile(
        name="reviewer",
        summary="Review plans and code changes for issues and risks.",
    ),
)


def list_agents() -> tuple[AgentProfile, ...]:
    """Return the built-in agent profiles in stable display order."""
    return _BUILT_IN_AGENTS
