"""Parser-only tests for reminder time expressions."""

from __future__ import annotations

from executive_assistant.tools.reminder_tools import _parse_time_expression


def test_parse_time_only_12h() -> None:
    dt = _parse_time_expression("11:22pm")
    assert dt.hour == 23
    assert dt.minute == 22


def test_parse_time_only_24h() -> None:
    dt = _parse_time_expression("23:22")
    assert dt.hour == 23
    assert dt.minute == 22


def test_parse_dotted_time_tonight() -> None:
    dt = _parse_time_expression("11.22pm tonight")
    assert dt.hour == 23
    assert dt.minute == 22


def test_parse_next_monday_with_time() -> None:
    dt = _parse_time_expression("next monday at 10am")
    assert dt.hour == 10
    assert dt.minute == 0

