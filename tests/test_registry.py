"""Tests for the initial built-in agent profile registry."""

from agentos.agents import get_agent_profile, list_agents


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


def test_profiles_have_non_empty_distinct_system_prompts() -> None:
    prompts = [profile.system_prompt for profile in list_agents()]

    assert len(prompts) == len(list_agents())
    assert all(prompt.strip() for prompt in prompts)
    assert len(set(prompts)) == len(prompts)


def test_profiles_state_their_action_limitations() -> None:
    for profile in list_agents():
        lowered = profile.system_prompt.lower()

        assert "never claim" in lowered
        assert "cannot" in lowered


def test_get_agent_profile_returns_known_agents() -> None:
    for profile in list_agents():
        assert get_agent_profile(profile.name) == profile


def test_get_agent_profile_rejects_unknown_names() -> None:
    assert get_agent_profile("missing-agent") is None
    assert get_agent_profile("") is None
    assert get_agent_profile("   ") is None
