from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from sqlalchemy.ext.asyncio import AsyncEngine


class PostgresConnection:
    """
    Async PostgreSQL connection manager for LangGraph state/checkpointing.

    This manages the connection to PostgreSQL for storing:
    - Agent sessions and threads
    - LangGraph checkpoints (state persistence)
    - Conversation history
    """

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    @property
    def engine(self) -> AsyncEngine:
        if self._engine is None:
            self._engine = create_async_engine(
                self.database_url,
                echo=False,
                pool_size=5,
                max_overflow=10,
            )
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        if self._session_factory is None:
            self._session_factory = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
        return self._session_factory

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession]:
        """Get an async database session."""
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def connect(self) -> None:
        """Establish database connection pool."""
        async with self.engine.begin() as conn:
            await conn.execute(text("SELECT 1"))

    async def disconnect(self) -> None:
        """Close database connection."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None

    async def execute(self, query: Any, params: dict[str, Any] | None = None) -> Any:
        """Execute a raw SQL query."""
        async with self.session() as session:
            result = await session.execute(query, params or {})
            return result

    async def fetch_one(self, query: Any, params: dict[str, Any] | None = None) -> Any:
        """Fetch a single row."""
        async with self.session() as session:
            result = await session.execute(query, params or {})
            return result.fetchone()

    async def fetch_all(self, query: Any, params: dict[str, Any] | None = None) -> list:
        """Fetch all rows."""
        async with self.session() as session:
            result = await session.execute(query, params or {})
            return result.fetchall()

    async def health_check(self) -> bool:
        """Check if the database connection is healthy."""
        try:
            async with self.session() as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception:
            return False


_postgres_connection: PostgresConnection | None = None


def get_postgres_connection(database_url: str | None = None) -> PostgresConnection:
    """
    Get the PostgreSQL connection singleton.

    Args:
        database_url: Database URL (only used on first call)

    Returns:
        PostgresConnection instance
    """
    global _postgres_connection

    if _postgres_connection is None:
        if database_url is None:
            from src.config.settings import get_settings

            settings = get_settings()
            database_url = settings.database_url

        _postgres_connection = PostgresConnection(database_url)

    return _postgres_connection


def reset_postgres_connection() -> None:
    """Reset the PostgreSQL connection singleton (useful for testing)."""
    global _postgres_connection
    _postgres_connection = None
