"""Tools for managing lightweight task state in agent state."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langgraph.types import Command
from langgraph.prebuilt.tool_node import ToolRuntime

from cassey.agent.state import TaskState


def _get_tool_runtime(**kwargs: Any) -> ToolRuntime | None:
    """Extract tool_runtime from kwargs, excluding it from args schema.

    The tool_runtime parameter is injected by LangGraph and cannot be
    included in the tool's JSON schema. We use **kwargs to hide it from
    the schema generation.
    """
    return kwargs.get("tool_runtime")


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _merge_state(base: TaskState | None, patch: TaskState) -> TaskState:
    merged: TaskState = dict(base or {})
    for key, value in patch.items():
        if value is None or value == "":
            continue
        merged[key] = value
    merged["updated_at"] = _now_iso()
    return merged


def _command_update(
    update: TaskState | None,
    message: str,
    tool_call_id: str | None,
    tool_name: str,
) -> Command:
    tool_message = ToolMessage(
        content=message,
        tool_call_id=tool_call_id or "",
        name=tool_name,
    )
    return Command(update={"task_state": update, "messages": [tool_message]})


@tool
def task_state_set(
    intent: str,
    target: str = "",
    next_action: str = "",
    status: str = "active",
    notes: str = "",
    **kwargs: Any,
) -> str | dict[str, Any] | Command:
    """Set the current task state for the thread."""
    tool_runtime = _get_tool_runtime(**kwargs)
    patch: TaskState = {
        "intent": intent,
        "target": target,
        "next_action": next_action,
        "status": status,
        "notes": notes,
        "updated_at": _now_iso(),
    }

    if tool_runtime is not None and tool_runtime.tool_call_id:
        return _command_update(
            update=patch,
            message="Task state set.",
            tool_call_id=tool_runtime.tool_call_id,
            tool_name="task_state_set",
        )

    return {"task_state": patch, "message": "Task state set."}


@tool
def task_state_update(
    intent: str = "",
    target: str = "",
    next_action: str = "",
    status: str = "",
    notes: str = "",
    **kwargs: Any,
) -> str | dict[str, Any] | Command:
    """Update fields in the current task state."""
    tool_runtime = _get_tool_runtime(**kwargs)
    patch: TaskState = {
        "intent": intent,
        "target": target,
        "next_action": next_action,
        "status": status,
        "notes": notes,
    }

    if tool_runtime is not None and tool_runtime.tool_call_id:
        current = None
        try:
            current = tool_runtime.state.get("task_state") if tool_runtime.state else None
        except Exception:
            current = None
        updated = _merge_state(current, patch)
        return _command_update(
            update=updated,
            message="Task state updated.",
            tool_call_id=tool_runtime.tool_call_id,
            tool_name="task_state_update",
        )

    return {"task_state_patch": patch, "message": "Task state updated."}


@tool
def task_state_clear(
    **kwargs: Any,
) -> str | dict[str, Any] | Command:
    """Clear the current task state."""
    tool_runtime = _get_tool_runtime(**kwargs)
    if tool_runtime is not None and tool_runtime.tool_call_id:
        return _command_update(
            update=None,
            message="Task state cleared.",
            tool_call_id=tool_runtime.tool_call_id,
            tool_name="task_state_clear",
        )
    return {"task_state": None, "message": "Task state cleared."}


@tool
def task_state_get(
    **kwargs: Any,
) -> str:
    """Get the current task state as JSON."""
    tool_runtime = _get_tool_runtime(**kwargs)
    if tool_runtime is None:
        return "Task state is unavailable in this runtime."
    state = tool_runtime.state.get("task_state") if tool_runtime.state else None
    return json.dumps(state or {}, indent=2)


def get_task_state_tools() -> list:
    """Get task state tools for agent use."""
    return [
        task_state_set,
        task_state_update,
        task_state_clear,
        task_state_get,
    ]
