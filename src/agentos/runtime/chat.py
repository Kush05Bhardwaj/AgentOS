"""Single-request chat runtime for AgentOS."""

import os
from collections.abc import Mapping, Sequence

from agentos.agents import get_agent_profile, list_agents
from agentos.config import ConfigurationError, Settings
from agentos.providers import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    create_provider,
    resolve_model_selection,
)


async def complete_chat(
    settings: Settings,
    messages: Sequence[ChatMessage],
    *,
    agent_name: str | None = None,
    provider_override: str | None = None,
    model_override: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> ChatResponse:
    """Execute one chat completion using resolved AgentOS settings.

    This function performs no planning, tool execution, or autonomous
    agent handoffs. It creates one provider, sends one request, returns
    the normalized response, and closes the provider.

    When a registered agent is selected, its system prompt is prepended
    to the supplied messages for this request only; the caller's message
    sequence is never modified or persisted with system messages.

    Args:
        settings: Configuration loaded and resolved by AgentOS.
        messages: Ordered chat messages to send to the model.
        agent_name: Optional agent whose profile and configuration
            should be used.
        provider_override: Explicit provider selection, such as a CLI option.
        model_override: Explicit model selection, such as a CLI option.
        environ: Optional environment mapping used for provider credentials.

    Returns:
        A provider-neutral ChatResponse.

    Raises:
        ConfigurationError: If the agent is unknown, or if a usable
            provider/model cannot be resolved.
        ProviderError: If the provider request fails.
    """
    environment = os.environ if environ is None else environ

    profile = None

    if agent_name is not None:
        profile = get_agent_profile(agent_name)

        if profile is None:
            supported = ", ".join(known.name for known in list_agents())
            raise ConfigurationError(
                f"Unknown agent '{agent_name.strip()}'. Supported agents: {supported}."
            )

    selection = resolve_model_selection(
        settings,
        agent_name=agent_name,
        provider_override=provider_override,
        model_override=model_override,
    )

    provider = create_provider(
        settings,
        provider_name=selection.provider,
        environ=environment,
    )

    request_messages: tuple[ChatMessage, ...] = tuple(messages)

    if profile is not None:
        request_messages = (
            ChatMessage(role="system", content=profile.system_prompt),
            *request_messages,
        )

    request = ChatRequest(
        model=selection.model,
        messages=request_messages,
        request_timeout_seconds=settings.general.request_timeout_seconds,
    )

    try:
        return await provider.complete(request)
    finally:
        await provider.aclose()
