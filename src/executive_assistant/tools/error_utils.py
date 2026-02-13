"""Utilities for consistent tool error handling."""

from __future__ import annotations

import asyncio
import logging
from functools import wraps
from typing import Any, Callable, TypeVar, cast

logger = logging.getLogger(__name__)

_F = TypeVar("_F", bound=Callable[..., Any])


def format_tool_error(exc: Exception) -> str:
    """Format a user-facing tool error string consistently."""
    message = str(exc).strip() or type(exc).__name__
    return f"Error: {message}"


def tool_error_boundary(func: _F) -> _F:
    """Catch unhandled tool exceptions and return a consistent error string.

    This keeps tool outputs deterministic for the agent/runtime while preserving
    stack traces in debug logs.
    """
    if asyncio.iscoroutinefunction(func):
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except Exception as exc:
                logger.debug(
                    "Tool %s failed: %s",
                    getattr(func, "__name__", "unknown_tool"),
                    exc,
                    exc_info=True,
                )
                return format_tool_error(exc)

        return cast(_F, async_wrapper)

    @wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            logger.debug(
                "Tool %s failed: %s",
                getattr(func, "__name__", "unknown_tool"),
                exc,
                exc_info=True,
            )
            return format_tool_error(exc)

    return cast(_F, sync_wrapper)
