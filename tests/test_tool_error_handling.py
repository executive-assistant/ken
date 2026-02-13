"""Tests for consistent tool error handling."""

from __future__ import annotations

import pytest

from executive_assistant.storage.thread_storage import clear_context
from executive_assistant.tools.error_utils import tool_error_boundary
from executive_assistant.tools.goals_tools import create_goal


def test_tool_error_boundary_sync_returns_error_string() -> None:
    @tool_error_boundary
    def _boom() -> str:
        raise ValueError("sync failure")

    result = _boom()
    assert result == "Error: sync failure"


@pytest.mark.asyncio
async def test_tool_error_boundary_async_returns_error_string() -> None:
    @tool_error_boundary
    async def _boom_async() -> str:
        raise RuntimeError("async failure")

    result = await _boom_async()
    assert result == "Error: async failure"


def test_goals_tool_returns_error_instead_of_raising_without_context() -> None:
    clear_context()
    result = create_goal.invoke({"title": "No context goal"})
    assert result == "Error: No thread_id in context."
