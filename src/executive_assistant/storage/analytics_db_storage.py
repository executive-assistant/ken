"""DuckDB storage for analytics queries (context-scoped)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

import duckdb

from executive_assistant.config import settings
from executive_assistant.storage.file_sandbox import get_thread_id
from executive_assistant.storage.group_storage import get_user_id, get_workspace_id
from executive_assistant.storage.helpers import sanitize_thread_id_to_user_id


Scope = Literal["context"]


def _get_analytics_db_path(scope: Scope = "context") -> Path:
    """Resolve the DuckDB analytics DB path for the current context.

    Priority (context scope):
    1) user_id
    2) group_id
    3) thread_id -> user_id
    """
    if scope != "context":
        raise ValueError("Analytics DB only supports scope='context' for now")

    user_id = get_user_id()
    if user_id:
        path = settings.get_user_root(user_id) / "analytics"
        path.mkdir(parents=True, exist_ok=True)
        return path / "duckdb.db"

    group_id = get_workspace_id()
    if group_id:
        path = settings.get_group_root(group_id) / "analytics"
        path.mkdir(parents=True, exist_ok=True)
        return path / "duckdb.db"

    thread_id = get_thread_id()
    if not thread_id:
        raise ValueError("No context (user_id, group_id, or thread_id) available")

    user_id = sanitize_thread_id_to_user_id(thread_id)
    path = settings.get_user_root(user_id) / "analytics"
    path.mkdir(parents=True, exist_ok=True)
    return path / "duckdb.db"


@lru_cache(maxsize=128)
def _get_duckdb_connection(db_path: Path) -> duckdb.DuckDBPyConnection:
    """Return a cached DuckDB connection for the given path."""
    return duckdb.connect(str(db_path))


def get_analytics_db(scope: Scope = "context") -> duckdb.DuckDBPyConnection:
    """Get a DuckDB connection for analytics in the current context."""
    db_path = _get_analytics_db_path(scope)
    return _get_duckdb_connection(db_path)
