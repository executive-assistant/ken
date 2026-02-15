from __future__ import annotations


class LLMError(Exception):
    """Base exception for LLM-related errors."""

    def __init__(self, message: str, provider: str | None = None) -> None:
        self.message = message
        self.provider = provider
        super().__init__(message)


class LLMConfigurationError(LLMError):
    """Raised when there's a configuration issue with an LLM provider."""

    pass


class LLMProviderNotFoundError(LLMError):
    """Raised when a requested LLM provider is not found or not registered."""

    def __init__(self, provider: str, message: str | None = None) -> None:
        self.provider = provider
        if message is None:
            message = f"LLM provider '{provider}' not found or not registered"
        super().__init__(message, provider=provider)


class LLMAuthenticationError(LLMError):
    """Raised when authentication with an LLM provider fails."""

    pass


class LLMRateLimitError(LLMError):
    """Raised when rate limit is exceeded for an LLM provider."""

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        retry_after: int | None = None,
    ) -> None:
        self.retry_after = retry_after
        super().__init__(message, provider=provider)


class LLMModelNotFoundError(LLMError):
    """Raised when a specific model is not found for a provider."""

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        model: str | None = None,
    ) -> None:
        self.model = model
        super().__init__(message, provider=provider)


class LLMConnectionError(LLMError):
    """Raised when connection to an LLM provider fails."""

    pass
