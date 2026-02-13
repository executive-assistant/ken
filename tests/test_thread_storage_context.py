"""Tests for thread/context storage isolation."""

from __future__ import annotations

import threading

from executive_assistant.storage.thread_storage import (
    clear_context,
    get_channel,
    get_chat_type,
    get_thread_id,
    set_channel,
    set_chat_type,
    set_thread_id,
)


def test_thread_id_not_visible_across_threads() -> None:
    """ContextVar state should not leak into a separate OS thread."""
    set_thread_id("http:user_a")

    result: dict[str, str | None] = {"thread_id": "unexpected"}

    def worker() -> None:
        result["thread_id"] = get_thread_id()

    t = threading.Thread(target=worker)
    t.start()
    t.join()

    assert result["thread_id"] is None


def test_clear_context_clears_thread_channel_and_chat_type() -> None:
    set_thread_id("telegram:123")
    set_channel("telegram")
    set_chat_type("private")

    clear_context()

    assert get_thread_id() is None
    assert get_channel() is None
    assert get_chat_type() is None
