from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from langchain.agents.middleware import AgentMiddleware
from langchain.messages import SystemMessage

if TYPE_CHECKING:
    from langchain.agents.middleware import ModelRequest, ModelResponse


class MemoryContextMiddleware(AgentMiddleware):
    """Inject relevant user memories into the system prompt.

    This middleware searches the user's memory database for relevant
    context before each model call and injects it into the system message.

    Usage:
        memory_db = MemoryDB(user_id="user-123")
        agent = create_deep_agent(
            model="gpt-4o",
            middleware=[MemoryContextMiddleware(memory_db)],
        )
    """

    def __init__(
        self,
        memory_db: Any,
        max_memories: int = 10,
        min_confidence: float = 0.7,
        include_types: list[str] | None = None,
    ) -> None:
        super().__init__()
        self.memory_db = memory_db
        self.max_memories = max_memories
        self.min_confidence = min_confidence
        self.include_types = include_types or ["semantic", "procedural"]

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        if not self.memory_db:
            return handler(request)

        query = self._extract_query(request)
        if not query:
            return handler(request)

        memories = self._search_memories(query)

        if not memories:
            return handler(request)

        memory_context = self._format_memories(memories)
        new_system = self._inject_context(request.system_message, memory_context)

        return handler(request.override(system_message=new_system))

    def _extract_query(self, request: ModelRequest) -> str:
        """Extract search query from the last user message."""
        for msg in reversed(request.messages):
            if msg.type == "human":
                content = msg.content
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            return block.get("text", "")
        return ""

    def _search_memories(self, query: str) -> list[dict]:
        """Search memory database for relevant memories."""
        try:
            return self.memory_db.search(
                query=query,
                limit=self.max_memories,
                min_confidence=self.min_confidence,
                types=self.include_types,
            )
        except Exception:
            return []

    def _format_memories(self, memories: list[dict]) -> str:
        """Format memories into context string."""
        if not memories:
            return ""

        lines = ["## User Context (from memory)"]
        lines.append("")

        for memory in memories:
            memory_type = memory.get("type", "unknown")
            content = memory.get("content", "")
            confidence = memory.get("confidence", 0)

            type_label = {
                "semantic": "Fact",
                "episodic": "Event",
                "procedural": "Rule",
            }.get(memory_type, memory_type)

            if confidence >= 0.9:
                lines.append(f"- **{type_label}**: {content}")
            else:
                lines.append(f"- {type_label}: {content}")

        lines.append("")
        return "\n".join(lines)

    def _inject_context(
        self,
        system_message: SystemMessage,
        memory_context: str,
    ) -> SystemMessage:
        """Inject memory context into system message."""
        existing_content = system_message.content

        if isinstance(existing_content, str):
            new_content = existing_content + "\n\n" + memory_context
        elif isinstance(existing_content, list):
            new_content = list(existing_content) + [
                {"type": "text", "text": "\n\n" + memory_context}
            ]
        else:
            new_content = str(existing_content) + "\n\n" + memory_context

        return SystemMessage(content=new_content)
