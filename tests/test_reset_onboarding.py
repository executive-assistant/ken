"""Tests for /reset all behavior and onboarding re-trigger marker."""

from __future__ import annotations

import pytest

from executive_assistant.channels.telegram import TelegramChannel
from executive_assistant.config.settings import settings


class _FakeConn:
    def __init__(self, executed: list[tuple[str, tuple[object, ...]]]) -> None:
        self._executed = executed

    async def execute(self, query: str, *args: object) -> None:
        self._executed.append((query, args))

    async def close(self) -> None:
        return None


@pytest.mark.asyncio
async def test_reset_all_creates_force_onboarding_marker(monkeypatch, tmp_path) -> None:
    """`/reset all` should clear thread data and force onboarding on next message."""
    thread_id = "telegram:12345"
    monkeypatch.setattr(settings, "USERS_ROOT", tmp_path)

    user_root = settings.get_thread_root(thread_id)
    (user_root / "tdb").mkdir(parents=True, exist_ok=True)
    (user_root / "tdb" / "db.sqlite").write_text("x")
    (user_root / "vdb").mkdir(parents=True, exist_ok=True)
    (user_root / "vdb" / "index.bin").write_text("x")
    (user_root / "files").mkdir(parents=True, exist_ok=True)
    (user_root / "files" / "note.txt").write_text("x")
    (user_root / "mem").mkdir(parents=True, exist_ok=True)
    (user_root / "mem" / "mem.db").write_text("x")
    (user_root / "agents").mkdir(parents=True, exist_ok=True)
    (user_root / "agents" / "agent.json").write_text("x")
    (user_root / "adb").mkdir(parents=True, exist_ok=True)
    (user_root / "adb" / "analytics.sqlite").write_text("x")

    executed: list[tuple[str, tuple[object, ...]]] = []

    async def _fake_connect(_dsn: str) -> _FakeConn:
        return _FakeConn(executed)

    monkeypatch.setattr("executive_assistant.channels.telegram.asyncpg.connect", _fake_connect)

    channel = TelegramChannel(token="test-token")
    result = await channel._execute_reset_scope("all", thread_id)

    assert "Reset complete" in result
    assert "onboarding state" in result

    # User root is recreated by force-onboarding marker creation.
    assert user_root.exists()
    assert (user_root / ".force_onboarding").exists()

    assert not (user_root / "tdb" / "db.sqlite").exists()
    assert not (user_root / "vdb").exists()
    assert not (user_root / "files").exists()
    assert not (user_root / "mem" / "mem.db").exists()
    assert not (user_root / "agents").exists()
    assert not (user_root / "adb").exists()

    # Ensure DB cleanup attempted for checkpoints/reminders/flows.
    sql = "\n".join(q for q, _ in executed)
    assert "DELETE FROM checkpoints" in sql
    assert "DELETE FROM reminders" in sql
    assert "DELETE FROM scheduled_flows" in sql
