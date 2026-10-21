"""Normalized provider error hierarchy for AgentOS."""


class ProviderError(Exception):
    """Base class for every provider failure.

    Implementations must raise subclasses of this error and must never
    place API keys or other secrets into the message.
    """


class AuthenticationError(ProviderError):
    """Credentials are missing or were rejected by the provider."""


class RateLimitError(ProviderError):
    """The provider is limiting how many requests may be made."""


class ProviderTimeoutError(ProviderError):
    """The provider did not respond within the request timeout."""


class ModelUnavailableError(ProviderError):
    """The requested model cannot be used with this provider."""


class InvalidProviderResponseError(ProviderError):
    """The provider returned a response that AgentOS cannot use."""
