"""Flow tools for APScheduler-backed executor chains."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from langchain_core.tools import tool

from executive_assistant.flows.spec import FlowSpec, AgentSpec, FlowMiddlewareConfig
from executive_assistant.flows.runner import build_flow_payload, run_flow_by_id
from executive_assistant.storage.file_sandbox import get_thread_id
from executive_assistant.storage.helpers import sanitize_thread_id_to_user_id
from executive_assistant.storage.scheduled_flows import get_scheduled_flow_storage
from executive_assistant.tools.reminder_tools import _parse_time_expression
from executive_assistant.utils.cron import parse_cron_next

FLOW_TOOL_NAMES = {"create_flow", "list_flows", "run_flow", "cancel_flow", "delete_flow"}


@tool
async def create_flow(
    name: str,
    description: str,
    agents: list[dict[str, Any]],
    schedule_type: str = "immediate",
    schedule_time: str | None = None,
    cron_expression: str | None = None,
    notify_on_complete: bool = False,
    notify_on_failure: bool = True,
    notification_channels: list[str] | None = None,
    run_mode: str = "normal",
    middleware: dict[str, Any] | None = None,
) -> str:
    """Create a flow (executor chain) for immediate, scheduled, or recurring execution."""
    thread_id = get_thread_id()
    if not thread_id:
        return "No thread context available to create a flow."

    owner = sanitize_thread_id_to_user_id(thread_id)
    flow_id = str(uuid.uuid4())

    schedule_type = schedule_type or "immediate"
    schedule_type = schedule_type.lower()

    due_time = datetime.now()

    if schedule_type == "scheduled":
        if not schedule_time:
            return "schedule_time is required for scheduled flows."
        due_time = _parse_time_expression(schedule_time)
    elif schedule_type == "recurring":
        if not cron_expression:
            return "cron_expression is required for recurring flows."
        due_time = parse_cron_next(cron_expression, datetime.now())
    elif schedule_type != "immediate":
        return "schedule_type must be immediate, scheduled, or recurring."

    forbidden = []
    for agent in agents:
        for tool_name in agent.get("tools", []):
            if tool_name in FLOW_TOOL_NAMES:
                forbidden.append(tool_name)
    if forbidden:
        return f"Flow agents may not use flow management tools: {sorted(set(forbidden))}"

    middleware_config = FlowMiddlewareConfig.model_validate(middleware or {})

    spec = FlowSpec(
        flow_id=flow_id,
        name=name,
        description=description,
        owner=owner,
        agents=[AgentSpec(**e) for e in agents],
        schedule_type=schedule_type,
        schedule_time=due_time if schedule_type == "scheduled" else None,
        cron_expression=cron_expression,
        notify_on_complete=notify_on_complete,
        notify_on_failure=notify_on_failure,
        notification_channels=notification_channels or [thread_id.split(":")[0]],
        run_mode=run_mode,
        middleware=middleware_config,
    )

    storage = await get_scheduled_flow_storage()
    payload = build_flow_payload(spec)
    flow = await storage.create(
        user_id=owner,
        thread_id=thread_id,
        task=description,
        flow=payload,
        due_time=due_time,
        name=name,
        cron=cron_expression,
    )

    return f"Flow created: {flow.id} ({spec.name}) scheduled for {due_time.isoformat()}"


@tool
async def list_flows(status: str | None = None) -> str:
    """List flows for the current user."""
    thread_id = get_thread_id()
    if not thread_id:
        return "No thread context available to list flows."

    owner = sanitize_thread_id_to_user_id(thread_id)
    storage = await get_scheduled_flow_storage()
    flows = await storage.list_by_user(owner, status=status)

    if not flows:
        return "No flows found."

    lines = []
    for flow in flows:
        lines.append(f"- [{flow.id}] {flow.name or '-'} — {flow.status} (due {flow.due_time})")

    return "\n".join(lines)


@tool
async def run_flow(flow_id: int) -> str:
    """Run a flow immediately by ID."""
    result = await run_flow_by_id(flow_id)
    return json.dumps(result, ensure_ascii=False)


@tool
async def cancel_flow(flow_id: int) -> str:
    """Cancel a pending flow by ID."""
    storage = await get_scheduled_flow_storage()
    success = await storage.cancel(flow_id)
    if success:
        return f"Flow {flow_id} cancelled."
    return f"Flow {flow_id} not found or not pending."


@tool
async def delete_flow(flow_id: int) -> str:
    """Delete a flow by ID."""
    storage = await get_scheduled_flow_storage()
    success = await storage.delete(flow_id)
    if success:
        return f"Flow {flow_id} deleted."
    return f"Flow {flow_id} not found."
