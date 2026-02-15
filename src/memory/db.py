"""Memory database interface and stub implementation.

This module provides a simple interface for the memory system
that can be used by middleware until the full implementation
with SQLite + FTS5 + vec is complete.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class Memory:
    """A single memory entry."""

    id: str
    content: str
    type: str  # semantic, episodic, procedural
    confidence: float = 0.7
    source: str = "explicit"  # explicit, learned, inferred
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_accessed: datetime | None = None
    access_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class MemoryDB:
    """In-memory stub for the memory database.

    This is a simple implementation for development/testing.
    The production implementation will use SQLite + FTS5 + vec.
    """

    def __init__(
        self,
        user_id: str,
        db_path: Path | None = None,
    ) -> None:
        self.user_id = user_id
        self.db_path = db_path
        self._memories: dict[str, Memory] = {}
        self._id_counter = 0

    def _generate_id(self) -> str:
        self._id_counter += 1
        return f"mem-{self._id_counter}"

    def add(
        self,
        content: str,
        memory_type: str = "semantic",
        confidence: float = 0.7,
        source: str = "explicit",
        metadata: dict[str, Any] | None = None,
    ) -> Memory:
        """Add a new memory."""
        memory = Memory(
            id=self._generate_id(),
            content=content,
            type=memory_type,
            confidence=confidence,
            source=source,
            metadata=metadata or {},
        )
        self._memories[memory.id] = memory
        return memory

    def get(self, memory_id: str) -> Memory | None:
        """Get a memory by ID."""
        memory = self._memories.get(memory_id)
        if memory:
            memory.last_accessed = datetime.now(timezone.utc)
            memory.access_count += 1
        return memory

    def update(
        self,
        memory_id: str,
        content: str | None = None,
        confidence: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Memory | None:
        """Update a memory."""
        memory = self._memories.get(memory_id)
        if not memory:
            return None

        if content is not None:
            memory.content = content
        if confidence is not None:
            memory.confidence = confidence
        if metadata is not None:
            memory.metadata.update(metadata)

        return memory

    def delete(self, memory_id: str) -> bool:
        """Delete a memory."""
        if memory_id in self._memories:
            del self._memories[memory_id]
            return True
        return False

    def search(
        self,
        query: str,
        limit: int = 10,
        min_confidence: float = 0.0,
        types: list[str] | None = None,
    ) -> list[dict]:
        """Search memories.

        This is a simple keyword search. Production implementation
        will use FTS5 for full-text search and vec for semantic search.
        """
        results = []
        query_lower = query.lower()

        for memory in self._memories.values():
            if memory.confidence < min_confidence:
                continue

            if types and memory.type not in types:
                continue

            if query_lower in memory.content.lower():
                results.append(
                    {
                        "id": memory.id,
                        "content": memory.content,
                        "type": memory.type,
                        "confidence": memory.confidence,
                        "source": memory.source,
                        "created_at": memory.created_at.isoformat(),
                        "last_accessed": memory.last_accessed.isoformat()
                        if memory.last_accessed
                        else None,
                    }
                )

        results.sort(key=lambda x: x["confidence"], reverse=True)
        return results[:limit]

    def get_all(
        self,
        types: list[str] | None = None,
        min_confidence: float = 0.0,
    ) -> list[Memory]:
        """Get all memories matching criteria."""
        results = []

        for memory in self._memories.values():
            if memory.confidence < min_confidence:
                continue
            if types and memory.type not in types:
                continue
            results.append(memory)

        return results

    def get_recent(
        self,
        days: int = 7,
        types: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """Get recent memories."""
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        results = []

        for memory in self._memories.values():
            if memory.created_at < cutoff:
                continue
            if types and memory.type not in types:
                continue

            results.append(
                {
                    "id": memory.id,
                    "content": memory.content,
                    "type": memory.type,
                    "confidence": memory.confidence,
                    "created_at": memory.created_at.isoformat(),
                }
            )

        results.sort(key=lambda x: x["created_at"], reverse=True)
        return results[:limit]

    def export_memories(self, min_confidence: float = 0.0) -> dict:
        """Export all memories for backup."""
        memories = []
        for memory in self._memories.values():
            if memory.confidence >= min_confidence:
                memories.append(
                    {
                        "content": memory.content,
                        "type": memory.type,
                        "confidence": memory.confidence,
                        "source": memory.source,
                        "metadata": memory.metadata,
                    }
                )

        return {
            "user_id": self.user_id,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "memories": memories,
            "count": len(memories),
        }

    def import_memories(
        self,
        data: dict,
        merge: bool = True,
    ) -> dict:
        """Import memories from backup."""
        imported = 0
        skipped = 0

        for memory_data in data.get("memories", []):
            if merge:
                self.add(
                    content=memory_data.get("content", ""),
                    memory_type=memory_data.get("type", "semantic"),
                    confidence=memory_data.get("confidence", 0.7),
                    source=memory_data.get("source", "imported"),
                    metadata=memory_data.get("metadata"),
                )
                imported += 1
            else:
                skipped += 1

        return {
            "imported": imported,
            "skipped": skipped,
        }

    def count(self) -> int:
        """Get total memory count."""
        return len(self._memories)
