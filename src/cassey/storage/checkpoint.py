"""Checkpoint storage configuration using PostgreSQL."""

import asyncio
from functools import partial
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg import Connection
from psycopg_pool import ConnectionPool

from cassey.config.settings import settings

# Global checkpointer instance
_checkpointer: BaseCheckpointSaver | None = None


class AsyncPostgresSaver(BaseCheckpointSaver):
    """
    Async-compatible wrapper for PostgresSaver.

    The standard PostgresSaver doesn't implement async methods.
    This wrapper adds async support by running sync methods in a thread pool.
    """

    def __init__(self, conn: Connection) -> None:
        self._saver = PostgresSaver(conn)

    # Delegate all sync methods to the underlying saver
    def get(self, config: Any, /, **kwargs: Any) -> Any:
        return self._saver.get(config, **kwargs)

    def get_tuple(self, config: Any, /, **kwargs: Any) -> Any:
        return self._saver.get_tuple(config, **kwargs)

    def list(self, config: Any, /, **kwargs: Any) -> Any:
        return self._saver.list(config, **kwargs)

    def put(
        self,
        config: Any,
        checkpoint: Any,
        metadata: Any,
        new_versions: Any,
        **kwargs: Any,
    ) -> Any:
        return self._saver.put(config, checkpoint, metadata, new_versions, **kwargs)

    def put_writes(
        self,
        config: Any,
        writes: Any,
        task_id: str,
        task_path: str = "",
        **kwargs: Any,
    ) -> Any:
        return self._saver.put_writes(config, writes, task_id, task_path, **kwargs)

    # Implement async methods using asyncio.to_thread
    async def aget(self, config: Any, /, **kwargs: Any) -> Any:
        return await asyncio.to_thread(self.get, config, **kwargs)

    async def aget_tuple(self, config: Any, /, **kwargs: Any) -> Any:
        return await asyncio.to_thread(self.get_tuple, config, **kwargs)

    async def alist(self, config: Any, /, **kwargs: Any) -> Any:
        return await asyncio.to_thread(self.list, config, **kwargs)

    async def aput(
        self,
        config: Any,
        checkpoint: Any,
        metadata: Any,
        new_versions: Any,
        **kwargs: Any,
    ) -> Any:
        return await asyncio.to_thread(
            self.put, config, checkpoint, metadata, new_versions, **kwargs
        )

    async def aput_writes(
        self,
        config: Any,
        writes: Any,
        task_id: str,
        task_path: str = "",
        **kwargs: Any,
    ) -> Any:
        return await asyncio.to_thread(
            self.put_writes, config, writes, task_id, task_path, **kwargs
        )

    # Pass through other attributes
    def __getattr__(self, name: str) -> Any:
        return getattr(self._saver, name)

    @property
    def conn(self) -> Connection:
        return self._saver.conn


def get_checkpointer(
    storage_type: str | None = None,
    connection_string: str | None = None,
):
    """
    Get a checkpointer instance for conversation state persistence.

    Note: For PostgreSQL with async operations, use get_async_checkpointer().

    Args:
        storage_type: Storage backend ("postgres", "memory").
        connection_string: Database connection string.

    Returns:
        Configured checkpointer instance.
    """
    storage = storage_type or settings.CHECKPOINT_STORAGE

    if storage == "postgres":
        # For postgres, we need async - use memory as fallback
        return MemorySaver()

    else:  # memory
        return MemorySaver()


async def get_async_checkpointer(
    storage_type: str | None = None,
    connection_string: str | None = None,
):
    """
    Get an async checkpointer instance for conversation state persistence.

    This creates an AsyncPostgresSaver for PostgreSQL.

    Args:
        storage_type: Storage backend ("postgres", "memory").
        connection_string: Database connection string.

    Returns:
        Configured async checkpointer instance.
    """
    global _checkpointer

    storage = storage_type or settings.CHECKPOINT_STORAGE

    if storage == "postgres":
        # Return existing checkpointer if already initialized
        if _checkpointer is not None:
            return _checkpointer

        conn_string = connection_string or settings.POSTGRES_URL

        # Create sync connection
        conn = Connection.connect(
            conn_string,
            autocommit=True,
            prepare_threshold=0,
        )

        # Create async-compatible wrapper
        _checkpointer = AsyncPostgresSaver(conn)

        # Initialize the schema
        _checkpointer._saver.setup()

        return _checkpointer

    else:  # memory
        _checkpointer = MemorySaver()
        return _checkpointer


async def close_checkpointer() -> None:
    """Close the checkpointer connection if applicable."""
    global _checkpointer

    if _checkpointer is not None and hasattr(_checkpointer, 'conn'):
        _checkpointer.conn.close()
        _checkpointer = None
