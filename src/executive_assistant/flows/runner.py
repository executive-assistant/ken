"""Flow execution runner for APScheduler-backed flows."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from langchain_core.messages import HumanMessage

from executive_assistant.config import settings, create_model
from executive_assistant.agent.langchain_state import ExecutiveAssistantAgentState
from executive_assistant.flows.spec import FlowSpec, AgentSpec, FlowMiddlewareConfig
from executive_assistant.storage.file_sandbox import set_thread_id, clear_thread_id
from executive_assistant.storage.helpers import sanitize_thread_id_to_user_id
from executive_assistant.storage.scheduled_flows import ScheduledFlow, get_scheduled_flow_storage
from executive_assistant.tools.registry import get_tools_by_name
from executive_assistant.utils.cron import parse_cron_next

logger = logging.getLogger(__name__)

FLOW_TOOL_NAMES = {"create_flow", "list_flows", "run_flow", "cancel_flow", "delete_flow"}


def _parse_flow_spec(flow_payload: str, owner: str) -> FlowSpec:
    data = json.loads(flow_payload)
    if "owner" not in data:
        data["owner"] = owner
    return FlowSpec.model_validate(data)


def _build_flow_middleware(config: FlowMiddlewareConfig, run_mode: str) -> list[Any]:
    middleware: list[Any] = []

    try:
        from langchain.agents.middleware import (
            ModelCallLimitMiddleware,
            ToolCallLimitMiddleware,
            ToolRetryMiddleware,
            ModelRetryMiddleware,
        )
    except Exception as exc:  # pragma: no cover - defensive
        raise RuntimeError(
            "LangChain middleware could not be imported. Ensure langchain>=1.0 is installed."
        ) from exc

    model_call_limit = config.model_call_limit
    tool_call_limit = config.tool_call_limit

    if model_call_limit is None:
        model_call_limit = settings.MW_MODEL_CALL_LIMIT
    if tool_call_limit is None:
        tool_call_limit = settings.MW_TOOL_CALL_LIMIT

    if model_call_limit and model_call_limit > 0:
        middleware.append(ModelCallLimitMiddleware(run_limit=model_call_limit))

    if tool_call_limit and tool_call_limit > 0:
        middleware.append(ToolCallLimitMiddleware(run_limit=tool_call_limit))

    if config.tool_retry_enabled:
        middleware.append(ToolRetryMiddleware())

    if config.model_retry_enabled:
        middleware.append(ModelRetryMiddleware())

    if run_mode == "emulated":
        try:
            from langchain.agents.middleware import LLMToolEmulator

            emulator = None
            try:
                emulator = LLMToolEmulator(tools=config.tool_emulator_tools or None)
            except Exception:
                emulator = LLMToolEmulator()

            middleware.append(emulator)
        except Exception as exc:
            logger.warning(f"LLMToolEmulator unavailable; skipping: {exc}")

    return middleware


def _build_prompt(system_prompt: str, previous_outputs: dict[str, Any]) -> str:
    if not previous_outputs:
        return system_prompt
    return system_prompt.replace(
        "$previous_output",
        json.dumps(previous_outputs, indent=2, ensure_ascii=False),
    )


def _extract_structured_output(content: str, schema: dict) -> dict:
    if not schema:
        return {"raw": content}

    try:
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            payload = content[start : end + 1]
            return json.loads(payload)
    except Exception:
        pass

    raise ValueError("Agent output did not contain valid JSON payload")


async def _run_agent(
    agent_spec: AgentSpec,
    previous_outputs: dict[str, Any],
    run_mode: str,
    middleware_config: FlowMiddlewareConfig,
) -> dict:
    model = create_model(model=agent_spec.model)
    tools = await get_tools_by_name([name for name in agent_spec.tools if name not in FLOW_TOOL_NAMES])

    prompt = _build_prompt(agent_spec.system_prompt, previous_outputs)

    try:
        from langchain.agents import create_agent
    except Exception as exc:
        raise RuntimeError(
            "LangChain create_agent is required. Ensure langchain>=1.0 is installed."
        ) from exc

    middleware = _build_flow_middleware(middleware_config, run_mode)

    agent_runner = create_agent(
        model=model,
        tools=tools,
        system_prompt=prompt,
        middleware=middleware,
        state_schema=ExecutiveAssistantAgentState,
    )

    result = await agent_runner.ainvoke({"messages": [HumanMessage(content="Execute your task.")]})
    content = getattr(result, "content", "") if result else ""
    return _extract_structured_output(content, agent_spec.output_schema)


async def execute_flow(flow: ScheduledFlow) -> dict:
    storage = await get_scheduled_flow_storage()
    thread_id = flow.thread_id
    owner = sanitize_thread_id_to_user_id(thread_id)

    try:
        flow_spec = _parse_flow_spec(flow.flow, owner)
    except Exception as exc:
        await storage.mark_failed(flow.id, f"Invalid flow spec: {exc}")
        raise

    set_thread_id(thread_id)
    now = datetime.now()

    try:
        await storage.mark_started(flow.id, started_at=now)
        previous_outputs: dict[str, Any] = {}
        results: list[dict[str, Any]] = []

        for agent_spec in flow_spec.agents:
            output = await _run_agent(
                agent_spec,
                previous_outputs,
                flow_spec.run_mode,
                flow_spec.middleware,
            )
            previous_outputs[agent_spec.agent_id] = output
            results.append(
                {
                    "agent_id": agent_spec.agent_id,
                    "status": "success",
                    "output": output,
                }
            )

        result_payload = json.dumps({"results": results}, ensure_ascii=False)
        await storage.mark_completed(flow.id, result=result_payload, completed_at=datetime.now())

        if flow_spec.notify_on_complete:
            from executive_assistant.scheduler import send_notification

            for channel in flow_spec.notification_channels:
                await send_notification([thread_id], f"Flow completed: {flow_spec.name}", channel)

        # Handle recurring flows
        if flow_spec.cron_expression:
            next_due = parse_cron_next(flow_spec.cron_expression, datetime.now())
            await storage.create_next_instance(flow, next_due)

        return {"status": "completed", "results": results}

    except Exception as exc:
        await storage.mark_failed(flow.id, str(exc), completed_at=datetime.now())
        if flow_spec.notify_on_failure:
            from executive_assistant.scheduler import send_notification

            for channel in flow_spec.notification_channels:
                await send_notification([thread_id], f"Flow failed: {flow_spec.name}", channel)
        raise
    finally:
        clear_thread_id()


async def run_flow_by_id(flow_id: int) -> dict:
    storage = await get_scheduled_flow_storage()
    flow = await storage.get_by_id(flow_id)
    if not flow:
        raise ValueError(f"Flow {flow_id} not found")
    return await execute_flow(flow)


def build_flow_payload(spec: FlowSpec) -> str:
    return spec.model_dump_json()
