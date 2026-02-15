from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from langchain.agents.middleware import AgentMiddleware

if TYPE_CHECKING:
    from langchain.agents.middleware import AgentState
    from langgraph.runtime import Runtime


class MemoryLearningMiddleware(AgentMiddleware):
    """Automatically extract and save memories from conversations.

    This middleware runs after the agent completes and extracts
    semantic, episodic, and procedural memories from the conversation.

    Usage:
        memory_db = MemoryDB(user_id="user-123")
        agent = create_deep_agent(
            model="gpt-4o",
            middleware=[MemoryLearningMiddleware(memory_db)],
        )
    """

    def __init__(
        self,
        memory_db: Any,
        extraction_model: Any | None = None,
        auto_learn: bool = True,
        min_confidence: float = 0.6,
    ) -> None:
        super().__init__()
        self.memory_db = memory_db
        self.extraction_model = extraction_model
        self.auto_learn = auto_learn
        self.min_confidence = min_confidence

    def after_agent(
        self,
        state: AgentState,
        runtime: Runtime,
    ) -> dict[str, Any] | None:
        """Extract memories after conversation completes."""
        if not self.auto_learn or not self.memory_db:
            return None

        messages = state.get("messages", [])
        if len(messages) < 2:
            return None

        try:
            memories = self._extract_memories(messages)

            for memory in memories:
                if memory.get("confidence", 0) >= self.min_confidence:
                    self._save_memory(memory)

        except Exception as e:
            pass

        return None

    def _extract_memories(self, messages: list) -> list[dict]:
        """Extract memories from conversation messages."""
        memories = []

        conversation_text = self._format_conversation(messages)

        if self.extraction_model:
            return self._llm_extraction(conversation_text)

        return self._rule_extraction(messages)

    def _format_conversation(self, messages: list) -> str:
        """Format messages into a single string."""
        lines = []
        for msg in messages:
            role = msg.type if hasattr(msg, "type") else "unknown"
            content = msg.content if hasattr(msg, "content") else str(msg)

            if role == "human":
                lines.append(f"User: {content}")
            elif role == "ai":
                lines.append(f"Assistant: {content}")

        return "\n".join(lines)

    def _llm_extraction(self, conversation: str) -> list[dict]:
        """Use LLM to extract memories from conversation."""
        from langchain.messages import HumanMessage, SystemMessage

        prompt = f"""Analyze this conversation and extract important information about the user.

For each piece of information, determine:
1. type: "semantic" (facts), "episodic" (events), or "procedural" (preferences/rules)
2. content: The information in a clear, concise statement
3. confidence: How confident you are (0.0-1.0)

Conversation:
{conversation}

Return a JSON array of memories. Example:
[
  {{"type": "semantic", "content": "User prefers TypeScript over JavaScript", "confidence": 0.9}},
  {{"type": "procedural", "content": "Always explain code changes before implementing", "confidence": 0.8}}
]

Only extract meaningful, non-obvious information. Return empty array if nothing significant."""

        try:
            response = self.extraction_model.invoke(
                [SystemMessage(content=prompt), HumanMessage(content="Extract memories now.")]
            )

            content = response.content
            if isinstance(content, str):
                start = content.find("[")
                end = content.rfind("]") + 1
                if start >= 0 and end > start:
                    return json.loads(content[start:end])
        except Exception:
            pass

        return []

    def _rule_extraction(self, messages: list) -> list[dict]:
        """Extract memories using simple rules (no LLM)."""
        memories = []

        for msg in messages:
            content = msg.content if hasattr(msg, "content") else ""
            if not isinstance(content, str):
                continue

            content_lower = content.lower()

            if self._contains_preference(content_lower):
                preference = self._extract_preference(content)
                if preference:
                    memories.append(
                        {
                            "type": "procedural",
                            "content": preference,
                            "confidence": 0.7,
                            "source": "learned",
                        }
                    )

            if self._contains_fact(content_lower):
                fact = self._extract_fact(content)
                if fact:
                    memories.append(
                        {
                            "type": "semantic",
                            "content": fact,
                            "confidence": 0.8,
                            "source": "explicit",
                        }
                    )

        return memories

    def _contains_preference(self, text: str) -> bool:
        """Check if text contains a preference indicator."""
        indicators = [
            "i prefer",
            "i like",
            "i'd rather",
            "my preference",
            "always use",
            "never use",
            "please use",
        ]
        return any(ind in text for ind in indicators)

    def _contains_fact(self, text: str) -> bool:
        """Check if text contains a fact about the user."""
        indicators = [
            "i am",
            "i work",
            "my name is",
            "my role is",
            "i'm a",
            "i'm working on",
            "my project",
        ]
        return any(ind in text for ind in indicators)

    def _extract_preference(self, text: str) -> str | None:
        """Extract a preference from text."""
        text_lower = text.lower()

        for indicator in ["i prefer", "i like", "i'd rather", "my preference is"]:
            if indicator in text_lower:
                idx = text_lower.find(indicator)
                preference = text[idx + len(indicator) :].strip()
                if len(preference) > 10 and len(preference) < 200:
                    return f"User prefers {preference}"

        return None

    def _extract_fact(self, text: str) -> str | None:
        """Extract a fact from text."""
        text_lower = text.lower()

        for indicator in ["i am", "i work", "my role is", "i'm a"]:
            if indicator in text_lower:
                idx = text_lower.find(indicator)
                fact = text[idx:].strip()
                if len(fact) > 10 and len(fact) < 200:
                    return fact

        return None

    def _save_memory(self, memory: dict) -> None:
        """Save a memory to the database."""
        try:
            self.memory_db.add(
                content=memory.get("content", ""),
                memory_type=memory.get("type", "semantic"),
                confidence=memory.get("confidence", 0.7),
                source=memory.get("source", "learned"),
            )
        except Exception:
            pass
