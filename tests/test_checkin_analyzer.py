"""Tests for check-in analyzer response parsing."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage

from executive_assistant.checkin import analyzer


@pytest.mark.asyncio
async def test_analyze_journal_and_goals_handles_ai_message(monkeypatch) -> None:
    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(return_value=AIMessage(content="Focus on stalled tasks"))
    monkeypatch.setattr(analyzer, "create_model", lambda: fake_llm)

    result = await analyzer.analyze_journal_and_goals([], [], "user-1")
    assert result == "Focus on stalled tasks"


@pytest.mark.asyncio
async def test_analyze_journal_and_goals_handles_ai_message_content_list(monkeypatch) -> None:
    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(
        return_value=AIMessage(content=[{"type": "text", "text": "Goal due soon"}])
    )
    monkeypatch.setattr(analyzer, "create_model", lambda: fake_llm)

    result = await analyzer.analyze_journal_and_goals([], [], "user-1")
    assert result == "Goal due soon"


@pytest.mark.asyncio
async def test_analyze_journal_and_goals_returns_checkin_ok(monkeypatch) -> None:
    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(return_value=AIMessage(content="CHECKIN_OK"))
    monkeypatch.setattr(analyzer, "create_model", lambda: fake_llm)

    result = await analyzer.analyze_journal_and_goals([], [], "user-1")
    assert result == "CHECKIN_OK"
