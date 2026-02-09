"""Tests for current LangChain agent runtime wiring."""

from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.graph.message import add_messages

from executive_assistant.agent.state import AgentState
from executive_assistant.agent.langchain_agent import (
    _normalize_agent_tools,
    create_langchain_agent,
)
from executive_assistant.agent.langchain_state import ExecutiveAssistantAgentState


class TestAgentState:
    """Validate AgentState shape used by the runtime."""

    def test_agent_state_structure(self) -> None:
        state = AgentState(
            messages=[HumanMessage(content="Hello")],
            user_id="test_user",
            channel="test",
        )

        assert len(state["messages"]) == 1
        assert state["messages"][0].content == "Hello"
        assert state["user_id"] == "test_user"
        assert state["channel"] == "test"

    def test_state_message_accumulation(self) -> None:
        existing = [HumanMessage(content="Hello"), AIMessage(content="Hi there")]
        new = [AIMessage(content="How can I help?")]

        result = add_messages(existing, new)
        assert len(result) == 3
        assert result[2].content == "How can I help?"


class TestAgentBuilder:
    """Validate create_langchain_agent integration contract."""

    def test_agent_module_exports_current_runtime(self) -> None:
        from executive_assistant import agent

        assert hasattr(agent, "AgentState")
        assert hasattr(agent, "create_langchain_agent")

    def test_normalize_agent_tools_keeps_structured_tools(self) -> None:
        @tool
        def sample_tool(text: str) -> str:
            """Return the same text."""
            return text

        normalized = _normalize_agent_tools([sample_tool])
        assert len(normalized) == 1
        assert normalized[0] is sample_tool

    def test_create_langchain_agent_delegates_to_langchain(self) -> None:
        mock_model = MagicMock()
        mock_tools = []
        mock_checkpointer = MagicMock()
        sentinel_runnable = MagicMock()
        mock_create_agent = MagicMock(return_value=sentinel_runnable)

        with patch(
            "executive_assistant.agent.langchain_agent._load_create_agent",
            return_value=mock_create_agent,
        ), patch(
            "executive_assistant.agent.langchain_agent._build_middleware",
            return_value=["mw1"],
        ):
            runnable = create_langchain_agent(
                model=mock_model,
                tools=mock_tools,
                checkpointer=mock_checkpointer,
                system_prompt="system prompt",
                channel=None,
            )

        assert runnable is sentinel_runnable
        mock_create_agent.assert_called_once_with(
            model=mock_model,
            tools=[],
            system_prompt="system prompt",
            middleware=["mw1"],
            state_schema=ExecutiveAssistantAgentState,
            checkpointer=mock_checkpointer,
        )
