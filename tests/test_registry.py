"""Tests for the initial built-in agent profile registry."""

from agentos.agents import list_agents


def test_agent_names_are_unique() -> None:
    names = [profile.name for profile in list_agents()]

    assert len(names) == len(set(names))


def test_registry_has_expected_initial_profiles() -> None:
    assert {profile.name for profile in list_agents()} == {
        "architect",
        "coder",
        "researcher",
        "reviewer",
    }
