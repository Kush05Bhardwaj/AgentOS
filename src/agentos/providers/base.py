"""Asynchronous provider interface for AgentOS."""

from abc import ABC, abstractmethod

from agentos.providers.models import ChatRequest, ChatResponse


class ChatProvider(ABC):
    """Provider-neutral asynchronous chat completion interface.

    Implementations translate a ChatRequest into a vendor call and
    normalize failures into ProviderError subclasses so the rest of
    AgentOS never observes vendor-specific errors.
    """

    @abstractmethod
    async def complete(self, request: ChatRequest) -> ChatResponse:
        """Return a normalized completion for the given request.

        Raises:
            ProviderError: Any provider failure, using the most specific
                subclass that describes the problem.
        """

    async def aclose(self) -> None:
        """Release provider resources.

        Stateless providers can use this default implementation.
        Providers that own HTTP clients should override it.
        """
        return None
