"""Agent state definition for ReAct graph."""

from typing import Annotated, Sequence, TypedDict, Any

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class TaskState(TypedDict, total=False):
    """Lightweight task state stored per thread."""

    intent: str
    target: str
    next_action: str
    status: str
    notes: str
    updated_at: str


class AgentState(TypedDict):
    """
    State that flows through all nodes in the ReAct agent graph.

    Attributes:
        messages: Accumulated message history with add_messages reducer.
        structured_summary: Topic-based structured summary with active/inactive topics.
        iterations: Number of reasoning cycles completed (prevents infinite loops).
        user_id: Identifier for the user (for multi-tenancy).
        channel: Source channel (telegram, slack, whatsapp, etc.).
        task_state: Lightweight task context for the current thread.
    """

    messages: Annotated[Sequence[BaseMessage], add_messages]
    structured_summary: dict[str, Any] | None
    iterations: int
    user_id: str
    channel: str
    task_state: TaskState | None
