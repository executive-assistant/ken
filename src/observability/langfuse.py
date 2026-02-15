from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from src.config.settings import get_settings

if TYPE_CHECKING:
    from collections.abc import Generator

    from langfuse import Langfuse


class LangfuseNoopClient:
    """
    No-op client for when Langfuse is disabled.

    All methods are no-ops that provide context managers
    to maintain the same interface as the real client.
    """

    def is_enabled(self) -> bool:
        return False

    @contextmanager
    def trace(
        self,
        name: str | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Generator[None]:
        yield None

    @contextmanager
    def span(
        self,
        name: str | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Generator[None]:
        yield None

    @contextmanager
    def generation(
        self,
        name: str | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Generator[None]:
        yield None

    def flush(self) -> None:
        pass

    def update_trace(
        self,
        trace_id: str,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        pass


class LangfuseClient:
    """
    Langfuse client wrapper for observability.

    Provides tracing, spans, and generation tracking for LLM calls.
    """

    def __init__(
        self,
        public_key: str | None,
        secret_key: str | None,
        host: str = "https://cloud.langfuse.com",
    ) -> None:
        self.public_key = public_key
        self.secret_key = secret_key
        self.host = host
        self._client: Langfuse | None = None

        if public_key and secret_key:
            try:
                from langfuse import Langfuse

                self._client = Langfuse(
                    public_key=public_key,
                    secret_key=secret_key,
                    host=host,
                )
            except ImportError:
                self._client = None

    def is_enabled(self) -> bool:
        return self._client is not None

    @contextmanager
    def trace(
        self,
        name: str | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Generator[Any]:
        if not self._client:
            yield None
            return

        trace = self._client.trace(name=name, metadata=metadata, **kwargs)
        yield trace

    @contextmanager
    def span(
        self,
        name: str | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Generator[Any]:
        if not self._client:
            yield None
            return

        span = self._client.span(name=name, metadata=metadata, **kwargs)
        yield span

    @contextmanager
    def generation(
        self,
        name: str | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Generator[Any]:
        if not self._client:
            yield None
            return

        gen = self._client.generation(name=name, metadata=metadata, **kwargs)
        yield gen

    def flush(self) -> None:
        if self._client:
            self._client.flush()

    def update_trace(
        self,
        trace_id: str,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        if self._client:
            self._client.trace(id=trace_id).update(metadata=metadata, **kwargs)


_langfuse_client: LangfuseClient | LangfuseNoopClient | None = None


def get_langfuse_client() -> LangfuseClient | LangfuseNoopClient:
    """
    Get the Langfuse client singleton.

    Returns a no-op client if Langfuse is not configured.
    """
    global _langfuse_client

    if _langfuse_client is None:
        settings = get_settings()

        if settings.is_langfuse_configured:
            _langfuse_client = LangfuseClient(
                public_key=settings.langfuse_public_key,
                secret_key=settings.langfuse_secret_key,
                host=settings.langfuse_host,
            )
        else:
            _langfuse_client = LangfuseNoopClient()

    return _langfuse_client


def is_langfuse_enabled() -> bool:
    """Check if Langfuse is enabled and configured."""
    settings = get_settings()
    return settings.is_langfuse_configured


@contextmanager
def trace_llm_call(
    provider: str,
    model: str,
    user_id: str | None = None,
    session_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> Generator[Any]:
    """
    Context manager for tracing LLM calls.

    Args:
        provider: LLM provider name (e.g., 'openai', 'anthropic')
        model: Model name (e.g., 'gpt-4o')
        user_id: Optional user identifier
        session_id: Optional session identifier
        metadata: Additional metadata

    Yields:
        Langfuse trace object or None if disabled
    """
    client = get_langfuse_client()

    trace_metadata = {
        "provider": provider,
        "model": model,
        **(metadata or {}),
    }

    with client.trace(
        name=f"llm_call_{provider}_{model}",
        user_id=user_id,
        session_id=session_id,
        metadata=trace_metadata,
    ) as trace:
        yield trace


def reset_langfuse_client() -> None:
    """Reset the Langfuse client singleton (useful for testing)."""
    global _langfuse_client
    _langfuse_client = None
