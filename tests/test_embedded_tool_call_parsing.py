"""Tests for parsing and executing embedded tool calls from model content."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.tools import tool

from executive_assistant.channels.base import BaseChannel


class _DummyChannel(BaseChannel):
    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    async def send_message(self, conversation_id: str, content: str, **kwargs) -> None:
        return None

    async def handle_message(self, message) -> None:
        return None


def _channel() -> _DummyChannel:
    agent = MagicMock()
    agent.ainvoke = AsyncMock(return_value={"messages": []})
    return _DummyChannel(agent=agent)


def test_extract_embedded_tool_calls_parses_deepseek_xml() -> None:
    channel = _channel()
    content = """
    <function_calls>
      <invoke name="add">
        <parameter name="a" string="false">2</parameter>
        <parameter name="b" string="false">3</parameter>
      </invoke>
      <invoke name="ping">
        <parameter name="x" string="true">hello</parameter>
      </invoke>
    </function_calls>
    """

    calls = channel._extract_embedded_tool_calls(content)
    assert calls == [
        {"name": "add", "arguments": {"a": 2, "b": 3}},
        {"name": "ping", "arguments": {"x": "hello"}},
    ]


def test_extract_embedded_tool_calls_parses_functioncalls_variant() -> None:
    channel = _channel()
    content = """
    <functioncalls>
      <invoke name="creatememory">
        <parameter name="content" string="true">Name is Eddy</parameter>
        <parameter name="memorytype" string="true">preference</parameter>
        <parameter name="key" string="true">userprofile</parameter>
      </invoke>
    </function_calls>
    """

    calls = channel._extract_embedded_tool_calls(content)
    assert calls == [
        {
            "name": "creatememory",
            "arguments": {
                "content": "Name is Eddy",
                "memorytype": "preference",
                "key": "userprofile",
            },
        }
    ]


@pytest.mark.asyncio
async def test_execute_embedded_tool_calls_executes_deepseek_xml(monkeypatch) -> None:
    channel = _channel()

    @tool
    async def add(a: int, b: int) -> str:
        """Add two integers."""
        return str(a + b)

    monkeypatch.setattr(
        "executive_assistant.tools.registry.get_all_tools",
        AsyncMock(return_value=[add]),
    )

    content = """
    <function_calls>
      <invoke name="add">
        <parameter name="a" string="false">5</parameter>
        <parameter name="b" string="false">7</parameter>
      </invoke>
    </function_calls>
    """

    outputs = await channel._execute_embedded_tool_calls(content)
    assert outputs == ["12"]


@pytest.mark.asyncio
async def test_execute_embedded_tool_calls_normalizes_tool_and_argument_aliases(monkeypatch) -> None:
    channel = _channel()

    @tool
    async def create_memory(content: str, memory_type: str = "fact", key: str = "") -> str:
        """Create memory."""
        return f"ok:{memory_type}:{key}:{content}"

    monkeypatch.setattr(
        "executive_assistant.tools.registry.get_all_tools",
        AsyncMock(return_value=[create_memory]),
    )

    content = """
    <functioncalls>
      <invoke name="creatememory">
        <parameter name="content" string="true">Name is Eddy</parameter>
        <parameter name="memorytype" string="true">preference</parameter>
        <parameter name="key" string="true">userprofile</parameter>
      </invoke>
    </function_calls>
    """

    outputs = await channel._execute_embedded_tool_calls(content)
    assert outputs == ["ok:preference:userprofile:Name is Eddy"]
