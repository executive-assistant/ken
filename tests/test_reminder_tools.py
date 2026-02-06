"""Comprehensive tests for reminder tools."""

from __future__ import annotations

from datetime import datetime, timedelta
import re
from typing import Generator
from uuid import uuid4

import pytest

from executive_assistant.storage.thread_storage import set_thread_id
from executive_assistant.tools.reminder_tools import (
    reminder_cancel,
    reminder_edit,
    reminder_list,
    reminder_set,
)


def _extract_id(result: str) -> int:
    match = re.search(r"ID:\s*(\d+)", result)
    assert match, f"Reminder ID not found in result: {result}"
    return int(match.group(1))


async def _call(tool, **kwargs) -> str:
    return await tool.ainvoke(kwargs)


@pytest.fixture
def test_thread_id() -> str:
    """Provide isolated thread ID per test."""
    return f"test_reminder_tools_{uuid4().hex[:10]}"


@pytest.fixture
def setup_thread_context(test_thread_id: str) -> Generator[None, None, None]:
    """Set up thread context for reminder operations."""
    set_thread_id(test_thread_id)
    yield


class TestReminderSet:
    async def test_set_reminder_absolute_time(self, setup_thread_context: None) -> None:
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
        result = await _call(reminder_set, message="Test reminder", time=tomorrow)
        assert "reminder set" in result.lower()

    async def test_set_reminder_relative_time(self, setup_thread_context: None) -> None:
        result = await _call(reminder_set, message="Reminder in 30 minutes", time="in 30 minutes")
        assert "reminder set" in result.lower()

    async def test_set_reminder_time_only_12h(self, setup_thread_context: None) -> None:
        result = await _call(reminder_set, message="Reminder at 11:22pm", time="11:22pm")
        assert "reminder set" in result.lower()

    async def test_set_reminder_time_only_24h(self, setup_thread_context: None) -> None:
        result = await _call(reminder_set, message="Reminder at 23:22", time="23:22")
        assert "reminder set" in result.lower()

    async def test_set_reminder_dotted_time_format(self, setup_thread_context: None) -> None:
        result = await _call(reminder_set, message="Go to sleep", time="11.22pm tonight")
        assert "reminder set" in result.lower()
        reminder_id = _extract_id(result)
        listed = await _call(reminder_list)
        assert "go to sleep" in listed.lower()
        assert str(reminder_id) in listed

    async def test_set_reminder_with_recurrence(self, setup_thread_context: None) -> None:
        result = await _call(
            reminder_set,
            message="Daily standup",
            time="tomorrow at 9am",
            recurrence="daily",
        )
        assert "reminder set" in result.lower()
        assert "recurring" in result.lower()


class TestReminderList:
    async def test_list_empty_reminders(self, setup_thread_context: None) -> None:
        result = await _call(reminder_list)
        assert "no reminders found" in result.lower()

    async def test_list_all_reminders(self, setup_thread_context: None) -> None:
        await _call(reminder_set, message="Reminder 1", time="in 1 hour")
        await _call(reminder_set, message="Reminder 2", time="in 2 hours")
        result = await _call(reminder_list)
        assert "reminder 1" in result.lower()
        assert "reminder 2" in result.lower()

    async def test_list_pending_reminders(self, setup_thread_context: None) -> None:
        await _call(reminder_set, message="Pending reminder", time="in 1 hour")
        result = await _call(reminder_list, status="pending")
        assert "pending reminder" in result.lower()

    async def test_list_invalid_status(self, setup_thread_context: None) -> None:
        result = await _call(reminder_list, status="completed")
        assert "invalid status" in result.lower()


class TestReminderCancel:
    async def test_cancel_pending_reminder(self, setup_thread_context: None) -> None:
        created = await _call(reminder_set, message="To be canceled", time="in 1 hour")
        reminder_id = _extract_id(created)
        result = await _call(reminder_cancel, reminder_id=reminder_id)
        assert "cancelled" in result.lower()

    async def test_cancel_nonexistent_reminder(self, setup_thread_context: None) -> None:
        result = await _call(reminder_cancel, reminder_id=99999)
        assert "not found" in result.lower()


class TestReminderEdit:
    async def test_edit_reminder_message(self, setup_thread_context: None) -> None:
        created = await _call(reminder_set, message="Original message", time="in 2 hours")
        reminder_id = _extract_id(created)
        result = await _call(reminder_edit, reminder_id=reminder_id, message="Updated message")
        assert "updated message" in result.lower()

    async def test_edit_reminder_time(self, setup_thread_context: None) -> None:
        created = await _call(reminder_set, message="Time test", time="in 2 hours")
        reminder_id = _extract_id(created)
        result = await _call(reminder_edit, reminder_id=reminder_id, time="in 3 hours")
        assert "updated" in result.lower()
        assert "time to" in result.lower()

    async def test_edit_nonexistent_reminder(self, setup_thread_context: None) -> None:
        result = await _call(reminder_edit, reminder_id=99999, message="Updated message")
        assert "not found" in result.lower()


class TestReminderWorkflows:
    async def test_reminder_lifecycle(self, setup_thread_context: None) -> None:
        created = await _call(reminder_set, message="Lifecycle test", time="in 3 hours")
        reminder_id = _extract_id(created)

        listed = await _call(reminder_list)
        assert "lifecycle test" in listed.lower()

        cancelled = await _call(reminder_cancel, reminder_id=reminder_id)
        assert "cancelled" in cancelled.lower()

    async def test_recurring_reminder_workflow(self, setup_thread_context: None) -> None:
        created = await _call(
            reminder_set,
            message="Weekly team meeting",
            time="next monday at 10am",
            recurrence="weekly",
        )
        assert "reminder set" in created.lower()
        listed = await _call(reminder_list)
        assert "weekly team meeting" in listed.lower()

    async def test_thread_isolation(self, setup_thread_context: None) -> None:
        await _call(reminder_set, message="Thread 1 reminder", time="in 1 hour")
        listed_current = await _call(reminder_list)
        assert "thread 1 reminder" in listed_current.lower()

        set_thread_id(f"different_thread_{uuid4().hex[:8]}")
        listed_other = await _call(reminder_list)
        assert "thread 1 reminder" not in listed_other.lower()

    async def test_time_expression_parsing(self, setup_thread_context: None) -> None:
        time_expressions = [
            ("in 5 minutes", "Relative time"),
            ("tomorrow at 9am", "Specific time tomorrow"),
            ("next monday", "Relative day"),
            ("11:22pm", "Time-only 12h"),
            ("23:22", "Time-only 24h"),
            ("11.22pm tonight", "Dotted chat time"),
        ]

        for time_expr, description in time_expressions:
            result = await _call(reminder_set, message=f"Test: {description}", time=time_expr)
            assert "reminder set" in result.lower(), f"Failed to parse {time_expr}: {result}"
