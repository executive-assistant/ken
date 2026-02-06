"""Reminder tools for the agent.

Tools for setting, listing, and canceling reminders.
Uses dateparser for flexible natural language date/time parsing.
"""

import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from langchain_core.tools import tool
import dateparser

from executive_assistant.config.settings import settings
from executive_assistant.storage.thread_storage import get_thread_id
from executive_assistant.storage.reminder import ReminderStorage, get_reminder_storage
from executive_assistant.storage.meta_registry import record_reminder_count


async def _get_storage() -> ReminderStorage:
    """Get reminder storage instance."""
    return await get_reminder_storage()


async def _refresh_reminder_meta(thread_id: str) -> None:
    """Refresh reminder count in meta registry."""
    try:
        storage = await _get_storage()
        reminders = await storage.list_by_thread(thread_id, None)
        record_reminder_count(thread_id, len(reminders))
    except Exception:
        return


def _normalize_time_expression(time_str: str) -> str:
    """Normalize common user-entered time variants before parsing."""
    normalized = time_str.strip()
    # Accept dotted times like "11.22pm tonight" -> "11:22pm tonight"
    normalized = re.sub(
        r"\b(\d{1,2})\.(\d{2})(\s*[ap]m\b)?",
        lambda m: f"{m.group(1)}:{m.group(2)}{m.group(3) or ''}",
        normalized,
        flags=re.IGNORECASE,
    )
    # Common chat phrasing variants for "tonight".
    normalized = re.sub(
        r"^\s*(\d{1,2}:\d{2}\s*[ap]m)\s+tonight\s*$",
        r"today at \1",
        normalized,
        flags=re.IGNORECASE,
    )
    normalized = re.sub(
        r"^\s*tonight(?:\s+at)?\s+(\d{1,2}:\d{2}\s*[ap]m)\s*$",
        r"today at \1",
        normalized,
        flags=re.IGNORECASE,
    )
    return normalized


def _has_explicit_date_context(time_str: str) -> bool:
    """Return True when expression includes date-like context words."""
    lowered = time_str.lower()
    date_keywords = {
        "today", "tonight", "tomorrow", "yesterday", "next", "last", "in",
        "week", "month", "year", "monday", "tuesday", "wednesday",
        "thursday", "friday", "saturday", "sunday", "jan", "feb",
        "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct",
        "nov", "dec", "-", "/",
    }
    return any(word in lowered for word in date_keywords)


def _looks_like_time_only(time_str: str) -> bool:
    """Return True when expression is a time without explicit date context."""
    return bool(re.match(r"^(at\s+)?\d{1,2}(:\d{2})?\s*(am|pm)?$", time_str.strip(), flags=re.IGNORECASE))


def _adjust_time_only_to_future(parsed: datetime, now: datetime, raw_time: str) -> datetime:
    """If user gave only a time and it already passed, roll forward one day."""
    if parsed < now and not _has_explicit_date_context(raw_time) and _looks_like_time_only(raw_time):
        return parsed + timedelta(days=1)
    return parsed


def _align_datetime_timezone(parsed: datetime, now: datetime) -> datetime:
    """Align parsed timezone awareness with `now` to avoid naive/aware comparisons."""
    if now.tzinfo and parsed.tzinfo is None:
        return parsed.replace(tzinfo=now.tzinfo)
    if not now.tzinfo and parsed.tzinfo:
        return parsed.replace(tzinfo=None)
    return parsed


def _to_storage_datetime(parsed: datetime) -> datetime:
    """Convert parsed datetimes into naive local time for DB storage.

    Reminders table currently uses TIMESTAMP (no tz). Normalize aware datetimes
    to local naive to avoid asyncpg offset-aware/naive binding errors.
    """
    if parsed.tzinfo is None:
        return parsed
    return parsed.astimezone().replace(tzinfo=None)


def _parse_next_weekday_expression(time_str: str, now: datetime) -> datetime | None:
    """Parse `next monday` and `next monday at 10am` style expressions."""
    match = re.match(
        r"^next\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)(?:\s+at\s+(.+))?$",
        time_str.strip(),
        flags=re.IGNORECASE,
    )
    if not match:
        return None

    weekday_name = match.group(1).lower()
    time_part = (match.group(2) or "").strip()
    weekday_map = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }
    target = weekday_map[weekday_name]
    days_ahead = (target - now.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7

    target_date = now + timedelta(days=days_ahead)
    if not time_part:
        return target_date.replace(hour=9, minute=0, second=0, microsecond=0)

    parsed_time = dateparser.parse(
        time_part,
        settings={
            "PREFER_DATES_FROM": "future",
            "RELATIVE_BASE": now,
            "STRICT_PARSING": False,
        },
    )
    if not parsed_time:
        return None

    return target_date.replace(
        hour=parsed_time.hour,
        minute=parsed_time.minute,
        second=0,
        microsecond=0,
    )


def _parse_time_expression(time_str: str, timezone: str | None = None) -> datetime:
    """Parse time expressions using dateparser.

    Supports many natural language formats:
    - Relative: "in 30 minutes", "in 2 hours", "in 3 days", "next week"
    - Days: "today", "tomorrow", "yesterday"
    - Combined: "today at 1:30pm", "tomorrow at 9am", "today 15:30"
    - Time only: "1:30pm", "3pm", "15:30" (assumes today, or tomorrow if passed)
    - Full datetime: "2025-01-15 14:00", "15 Jan 2025 2pm"
    - Relative dates: "next monday", "last friday", "in 2 weeks"

    Args:
        time_str: Time expression to parse
        timezone: Optional IANA timezone name (e.g., "America/New_York")

    Returns:
        datetime object representing the parsed time (timezone-aware if timezone provided)

    Raises:
        ValueError: If the time expression cannot be parsed
    """
    time_str = _normalize_time_expression(time_str)

    # Use timezone-aware now if timezone is provided
    if timezone:
        try:
            tz = ZoneInfo(timezone)
            now = datetime.now(tz)
        except Exception:
            # Invalid timezone, fall back to UTC
            now = datetime.now()
    else:
        now = datetime.now()

    weekday_dt = _parse_next_weekday_expression(time_str, now)
    if weekday_dt:
        return weekday_dt

    # Strict-ish configuration for richer natural-language date expressions.
    settings_config = {
        'PREFER_DATES_FROM': 'future',
        'RELATIVE_BASE': now,
        'STRICT_PARSING': False,
        'REQUIRE_PARTS': ['day'],  # At least day part required
    }

    # First try: use dateparser for most natural language expressions
    parsed = dateparser.parse(time_str, settings=settings_config)

    if parsed:
        parsed = _align_datetime_timezone(parsed, now)
        return _adjust_time_only_to_future(parsed, now, time_str)

    # Second try: relaxed parse to accept common time-only expressions.
    relaxed_settings = {
        'PREFER_DATES_FROM': 'future',
        'RELATIVE_BASE': now,
        'STRICT_PARSING': False,
    }
    parsed = dateparser.parse(time_str, settings=relaxed_settings)
    if parsed:
        parsed = _align_datetime_timezone(parsed, now)
        return _adjust_time_only_to_future(parsed, now, time_str)

    # Fallback for military time format like "1130hr", "1430hr" (edge case)
    military_match = re.search(r'(\d{4})hr\b', time_str)
    if military_match:
        time_digits = military_match.group(1)
        hour = int(time_digits[:2])
        minute = int(time_digits[2:])
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            parsed_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if parsed_time < now:
                parsed_time += timedelta(days=1)
            return parsed_time

    # Fallback for 4-digit military time without "hr" suffix
    if re.match(r'^\d{4}$', time_str):
        hour = int(time_str[:2])
        minute = int(time_str[2:])
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            parsed_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if parsed_time < now:
                parsed_time += timedelta(days=1)
            return parsed_time

    raise ValueError(
        f"Could not parse time expression '{time_str}'. "
        "Try formats like: 'in 30 minutes', 'in 2 hours', 'today at 1:30pm', "
        "'tomorrow at 9am', 'next monday', '1:30pm', '15:30', '2025-01-15 14:00'"
    )


@tool
async def reminder_set(
    message: str,
    time: str,
    recurrence: str = "",
    timezone: str = "",
) -> str:
    """Set a reminder for the user.

    Args:
        message: The reminder message (what to remind about)
        time: When to remind. Flexible formats supported via dateparser:
            - Relative: "in 30 minutes", "in 2 hours", "in 3 days", "next week"
            - Day + time: "today at 1:30pm", "tomorrow at 9am", "today 15:30"
            - Time only: "1:30pm", "3pm", "15:30" (assumes today/tomorrow)
            - Relative dates: "next monday", "next friday at 2pm"
            - Numeric: "0130hr" (1:30 AM), "1430hr" (2:30 PM)
            - Full date: "2025-01-15 14:00", "15 Jan 2025 2pm"
        recurrence: Optional recurrence pattern (e.g., "daily", "weekly", "daily at 9am")
        timezone: Optional IANA timezone name (e.g., "America/New_York", "Asia/Shanghai", "UTC").
                  If provided, the reminder time will be interpreted in this timezone.

    Returns:
        Confirmation message with reminder ID
    """
    storage = await _get_storage()
    thread_id = get_thread_id()

    if thread_id is None:
        return "Error: Could not determine conversation context for reminder."

    try:
        due_time = _parse_time_expression(time, timezone if timezone else None)
        due_time = _to_storage_datetime(due_time)
    except ValueError as e:
        return f"Error: {e}"

    try:
        reminder = await storage.create(
            thread_id=thread_id,
            message=message,
            due_time=due_time,
            recurrence=recurrence or None,
            timezone=timezone if timezone else None,
        )
    except Exception as e:
        return f"Error: failed to save reminder ({type(e).__name__}): {e}"

    await _refresh_reminder_meta(thread_id)
    recurrence_str = f" (recurring: {recurrence})" if recurrence else ""
    timezone_str = f" ({timezone})" if timezone else ""
    return f"Reminder set for {due_time.strftime('%Y-%m-%d %H:%M')}{timezone_str}{recurrence_str}. ID: {reminder.id}"


@tool
async def reminder_list(
    status: str = "",
) -> str:
    """List all reminders for the current thread.

    Args:
        status: Filter by status ('pending', 'sent', 'cancelled', 'failed'). Empty for all.

    Returns:
        Formatted list of reminders with timezone information
    """
    storage = await _get_storage()
    thread_id = get_thread_id()

    if thread_id is None:
        return "Error: Could not determine conversation context."

    # Validate status if provided
    valid_statuses = {"pending", "sent", "cancelled", "failed"}
    if status and status not in valid_statuses:
        return f"Invalid status. Use one of: {', '.join(valid_statuses)}"

    try:
        reminders = await storage.list_by_thread(thread_id, status or None)
    except Exception as e:
        return f"Error: failed to list reminders ({type(e).__name__}): {e}"

    if not reminders:
        return "No reminders found."

    record_reminder_count(thread_id, len(reminders))
    lines = [f"{'ID':<5} {'Status':<10} {'Due Time':<25} {'Message'}"]
    lines.append("-" * 80)

    for r in reminders:
        due_str = r.due_time.strftime("%Y-%m-%d %H:%M")
        timezone_str = f" {r.timezone}" if r.timezone else ""
        recurrence_str = " (recurring)" if r.is_recurring else ""
        lines.append(f"{r.id:<5} {r.status:<10} {due_str + timezone_str:<25} {r.message}{recurrence_str}")

    return "\n".join(lines)


@tool
async def reminder_cancel(
    reminder_id: int,
) -> str:
    """Cancel a pending reminder.

    Args:
        reminder_id: The ID of the reminder to cancel

    Returns:
        Confirmation message
    """
    storage = await _get_storage()
    thread_id = get_thread_id()

    if thread_id is None:
        return "Error: Could not determine conversation context."

    # Verify the reminder belongs to this user
    try:
        reminder = await storage.get_by_id(reminder_id)
    except Exception as e:
        return f"Error: failed to read reminder ({type(e).__name__}): {e}"

    if not reminder:
        return f"Reminder {reminder_id} not found."

    if reminder.thread_id != thread_id:
        return "You can only cancel your own reminders."

    if reminder.status != "pending":
        return f"Reminder {reminder_id} is not pending (status: {reminder.status})."

    try:
        await storage.cancel(reminder_id)
    except Exception as e:
        return f"Error: failed to cancel reminder ({type(e).__name__}): {e}"
    await _refresh_reminder_meta(thread_id)
    return f"Reminder {reminder_id} cancelled."


@tool
async def reminder_edit(
    reminder_id: int,
    message: str = "",
    time: str = "",
    timezone: str = "",
) -> str:
    """Edit an existing reminder.

    Args:
        reminder_id: The ID of the reminder to edit
        message: New reminder message (leave empty to keep current)
        time: New due time (leave empty to keep current)
        timezone: New timezone (e.g., "America/New_York", "Asia/Shanghai", "UTC").
                  Leave empty to keep current. Use "UTC" to remove timezone.

    Returns:
        Confirmation message
    """
    storage = await _get_storage()
    thread_id = get_thread_id()

    if thread_id is None:
        return "Error: Could not determine conversation context."

    # Verify ownership
    try:
        reminder = await storage.get_by_id(reminder_id)
    except Exception as e:
        return f"Error: failed to read reminder ({type(e).__name__}): {e}"

    if not reminder:
        return f"Reminder {reminder_id} not found."

    if reminder.thread_id != thread_id:
        return "You can only edit your own reminders."

    if reminder.status != "pending":
        return f"Reminder {reminder_id} is not pending (status: {reminder.status})."

    # Parse new values
    new_message = message if message else None
    new_due_time = None

    if time:
        try:
            # Use existing timezone if not specified
            tz = timezone if timezone else reminder.timezone
            new_due_time = _parse_time_expression(time, tz if tz else None)
            new_due_time = _to_storage_datetime(new_due_time)
        except ValueError as e:
            return f"Error: {e}"

    # Handle timezone update (empty string means no change, "UTC" or similar means set to that)
    new_timezone = None
    if timezone:
        new_timezone = timezone if timezone != "remove" else None

    try:
        updated = await storage.update(
            reminder_id,
            new_message,
            new_due_time,
            timezone=new_timezone,
        )
    except Exception as e:
        return f"Error: failed to update reminder ({type(e).__name__}): {e}"

    if updated:
        await _refresh_reminder_meta(thread_id)
        changes = []
        if new_message:
            changes.append(f"message to '{new_message}'")
        if new_due_time:
            tz_str = f" {updated.timezone}" if updated.timezone else ""
            changes.append(f"time to {new_due_time.strftime('%Y-%m-%d %H:%M')}{tz_str}")
        if new_timezone is not None:
            changes.append(f"timezone to {new_timezone if new_timezone else 'None'}")

        change_str = " and ".join(changes) if changes else "nothing"
        return f"Reminder {reminder_id} updated: {change_str}."
    else:
        return "Failed to update reminder."


def get_reminder_tools() -> list:
    """Get all reminder tools."""
    return [reminder_set, reminder_list, reminder_cancel, reminder_edit]
