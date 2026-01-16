"""Unit tests for LangChain agent runtime."""

import pytest

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver

from cassey.agent.langchain_agent import create_langchain_agent, _build_middleware
from cassey.config import settings


class ToolBindingFakeChatModel(GenericFakeChatModel):
    """Generic fake model that supports tool binding."""

    def bind_tools(self, tools, *, tool_choice=None, **kwargs):
        return self


def _build_tool_call():
    try:
        from langchain_core.messages import ToolCall

        return ToolCall(name="add", args={"a": 1, "b": 2}, id="call_1")
    except Exception:
        return {"name": "add", "args": {"a": 1, "b": 2}, "id": "call_1"}


def test_context_editing_middleware_enabled(monkeypatch):
    """ContextEditingMiddleware should be included when enabled."""
    from langchain.agents.middleware import ContextEditingMiddleware

    monkeypatch.setattr(settings, "MW_SUMMARIZATION_ENABLED", False)
    monkeypatch.setattr(settings, "MW_TOOL_RETRY_ENABLED", False)
    monkeypatch.setattr(settings, "MW_MODEL_RETRY_ENABLED", False)
    monkeypatch.setattr(settings, "MW_MODEL_CALL_LIMIT", 0)
    monkeypatch.setattr(settings, "MW_TOOL_CALL_LIMIT", 0)
    monkeypatch.setattr(settings, "MW_TODO_LIST_ENABLED", False)
    monkeypatch.setattr(settings, "MW_CONTEXT_EDITING_ENABLED", True)

    middleware = _build_middleware(ToolBindingFakeChatModel(messages=iter([])))
    assert any(isinstance(m, ContextEditingMiddleware) for m in middleware)


def test_context_editing_middleware_disabled(monkeypatch):
    """ContextEditingMiddleware should NOT be included when disabled (default)."""
    from langchain.agents.middleware import ContextEditingMiddleware

    monkeypatch.setattr(settings, "MW_SUMMARIZATION_ENABLED", False)
    monkeypatch.setattr(settings, "MW_TOOL_RETRY_ENABLED", False)
    monkeypatch.setattr(settings, "MW_MODEL_RETRY_ENABLED", False)
    monkeypatch.setattr(settings, "MW_MODEL_CALL_LIMIT", 0)
    monkeypatch.setattr(settings, "MW_TOOL_CALL_LIMIT", 0)
    monkeypatch.setattr(settings, "MW_TODO_LIST_ENABLED", False)
    monkeypatch.setattr(settings, "MW_CONTEXT_EDITING_ENABLED", False)

    middleware = _build_middleware(ToolBindingFakeChatModel(messages=iter([])))
    assert not any(isinstance(m, ContextEditingMiddleware) for m in middleware)


@pytest.mark.asyncio
async def test_langchain_agent_executes_tool(monkeypatch):
    """Agent should execute tool calls from the model response."""
    monkeypatch.setattr(settings, "MW_SUMMARIZATION_ENABLED", False)
    monkeypatch.setattr(settings, "MW_TOOL_RETRY_ENABLED", False)
    monkeypatch.setattr(settings, "MW_MODEL_RETRY_ENABLED", False)
    monkeypatch.setattr(settings, "MW_MODEL_CALL_LIMIT", 0)
    monkeypatch.setattr(settings, "MW_TOOL_CALL_LIMIT", 0)

    calls: list[tuple[int, int]] = []

    @tool
    def add(a: int, b: int) -> str:
        """Add two numbers."""
        calls.append((a, b))
        return str(a + b)

    model = ToolBindingFakeChatModel(
        messages=iter(
            [
                AIMessage(content="", tool_calls=[_build_tool_call()]),
                AIMessage(content="3"),
            ]
        )
    )

    agent = create_langchain_agent(
        model=model,
        tools=[add],
        checkpointer=InMemorySaver(),
        system_prompt="You are a test agent.",
    )

    result = await agent.ainvoke(
        {"messages": [HumanMessage(content="Add 1 and 2")]},
        config={"configurable": {"thread_id": "unit-test"}},
    )

    assert calls == [(1, 2)]
    assert any(
        getattr(message, "content", "") == "3"
        for message in result.get("messages", [])
    )
