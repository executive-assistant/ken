"""Tests for /reset all behavior and onboarding re-trigger marker."""

from __future__ import annotations

import pytest

from executive_assistant.channels.telegram import TelegramChannel
from executive_assistant.config.settings import settings
from executive_assistant.storage.sqlite_db_storage import get_sqlite_db, reset_connection_cache


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
    cache_reset_calls = 0

    async def _fake_connect(_dsn: str) -> _FakeConn:
        return _FakeConn(executed)

    def _fake_reset_connection_cache() -> None:
        nonlocal cache_reset_calls
        cache_reset_calls += 1

    monkeypatch.setattr("executive_assistant.channels.telegram.asyncpg.connect", _fake_connect)
    monkeypatch.setattr("executive_assistant.storage.sqlite_db_storage.reset_connection_cache", _fake_reset_connection_cache)

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
    assert cache_reset_calls == 1

    # Ensure DB cleanup attempted for checkpoints/reminders/flows.
    sql = "\n".join(q for q, _ in executed)
    assert "DELETE FROM checkpoints" in sql
    assert "DELETE FROM reminders" in sql
    assert "DELETE FROM scheduled_flows" in sql


@pytest.mark.asyncio
async def test_reset_tdb_clears_sqlite_cache(monkeypatch, tmp_path) -> None:
    """`/reset tdb` should clear SQLite cache before deleting DB file."""
    thread_id = "telegram:tdb-reset"
    monkeypatch.setattr(settings, "USERS_ROOT", tmp_path)

    user_root = settings.get_thread_root(thread_id)
    (user_root / "tdb").mkdir(parents=True, exist_ok=True)
    db_path = user_root / "tdb" / "db.sqlite"
    db_path.write_text("x")

    cache_reset_calls = 0

    def _fake_reset_connection_cache() -> None:
        nonlocal cache_reset_calls
        cache_reset_calls += 1

    monkeypatch.setattr("executive_assistant.storage.sqlite_db_storage.reset_connection_cache", _fake_reset_connection_cache)

    channel = TelegramChannel(token="test-token")
    result = await channel._execute_reset_scope("tdb", thread_id)

    assert "Reset complete" in result
    assert "tdb" in result
    assert cache_reset_calls == 1
    assert not db_path.exists()


@pytest.mark.asyncio
async def test_reset_tdb_removes_cached_table_state(monkeypatch, tmp_path) -> None:
    """Reset must clear cached SQLite handles so old tables are not visible."""
    thread_id = "telegram:tdb-cached-state"
    monkeypatch.setattr(settings, "USERS_ROOT", tmp_path)
    reset_connection_cache()

    db = get_sqlite_db(thread_id)
    db.create_table("timesheets", ["task TEXT"])
    assert "timesheets" in db.list_tables()

    channel = TelegramChannel(token="test-token")
    result = await channel._execute_reset_scope("tdb", thread_id)

    assert "Reset complete" in result
    assert "tdb" in result

    # Should now resolve to a fresh DB file with no previous schema.
    db_after = get_sqlite_db(thread_id)
    assert db_after.list_tables() == []
