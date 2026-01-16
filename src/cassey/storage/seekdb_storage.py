"""SeekDB storage helpers for per-workspace KB persistence."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from cassey.config import settings
from cassey.storage.file_sandbox import get_thread_id
from cassey.storage.user_registry import sanitize_thread_id
from cassey.storage.workspace_storage import get_workspace_id


def _require_seekdb_embedded() -> None:
    try:
        from pyseekdb.client.client_seekdb_embedded import _PYLIBSEEKDB_AVAILABLE  # type: ignore
    except Exception as exc:  # pragma: no cover - defensive
        raise RuntimeError("pyseekdb is not available. Install pyseekdb to use SeekDB KB.") from exc

    if not _PYLIBSEEKDB_AVAILABLE:
        raise RuntimeError(
            "SeekDB embedded mode is unavailable (pylibseekdb is Linux-only). "
            "Use a Linux runtime or provide a remote SeekDB server implementation."
        )


def _get_storage_id(thread_id: str | None = None, workspace_id: str | None = None) -> str:
    """
    Get the storage identifier (workspace_id or thread_id).

    Priority:
    1. workspace_id if provided (new workspace-based routing)
    2. workspace_id from context (new workspace-based routing)
    3. thread_id if provided (legacy thread-based routing)
    4. thread_id from context (legacy thread-based routing)

    Returns:
        The storage identifier (workspace_id or thread_id).
    """
    # Check workspace_id first
    if workspace_id is None:
        workspace_id = get_workspace_id()

    if workspace_id:
        return workspace_id

    # Fall back to thread_id
    if thread_id is None:
        thread_id = get_thread_id()

    if not thread_id:
        raise ValueError("No thread_id/workspace_id provided and none in context")

    return thread_id


def get_kb_storage_dir(thread_id: str | None = None, workspace_id: str | None = None) -> Path:
    """
    Return the KB directory for a workspace or thread.

    Args:
        thread_id: Thread identifier (legacy).
        workspace_id: Workspace identifier (new).

    Returns:
        Path to the KB directory.
    """
    storage_id = _get_storage_id(thread_id, workspace_id)
    safe_id = sanitize_thread_id(storage_id)

    # Check if this is a workspace ID (starts with "ws:") or thread ID
    # For workspace routing, use workspace path
    if storage_id.startswith("ws:") or storage_id.startswith("group:") or storage_id == "public":
        path = settings.get_workspace_kb_path(storage_id)
    else:
        # Legacy thread-based routing
        path = (settings.USERS_ROOT / safe_id / "kb").resolve()

    path.mkdir(parents=True, exist_ok=True)
    return path


# Legacy alias for backward compatibility
def get_thread_seekdb_dir(thread_id: str | None = None) -> Path:
    """Return the per-thread SeekDB directory (legacy, use get_kb_storage_dir)."""
    return get_kb_storage_dir(thread_id=thread_id)


@lru_cache(maxsize=128)
def get_seekdb_client(thread_id: str | None = None, workspace_id: str | None = None):
    """
    Get a cached SeekDB client for a workspace or thread.

    Args:
        thread_id: Thread identifier (legacy).
        workspace_id: Workspace identifier (new).

    Returns:
        SeekDB Client instance.
    """
    _require_seekdb_embedded()
    from pyseekdb import Client

    path = get_kb_storage_dir(thread_id, workspace_id)
    return Client(path=str(path), database=settings.SEEKDB_DATABASE)


def list_seekdb_collections(thread_id: str | None = None, workspace_id: str | None = None) -> list[str]:
    """
    List collection names for a workspace or thread.

    Args:
        thread_id: Thread identifier (legacy).
        workspace_id: Workspace identifier (new).

    Returns:
        List of collection names.
    """
    client = get_seekdb_client(thread_id, workspace_id)
    collections = client.list_collections()
    return [collection.name for collection in collections]


def get_seekdb_collection(thread_id: str, name: str, workspace_id: str | None = None):
    """
    Get an existing collection.

    Args:
        thread_id: Thread identifier (legacy, can be None if workspace_id provided).
        name: Collection name.
        workspace_id: Workspace identifier (new).

    Returns:
        SeekDB Collection instance.
    """
    client = get_seekdb_client(thread_id, workspace_id)
    return client.get_collection(name)


def create_seekdb_collection(thread_id: str, name: str, embedding_function: Any, workspace_id: str | None = None):
    """
    Create a collection with optional embedding and full-text configuration.

    Args:
        thread_id: Thread identifier (legacy, can be None if workspace_id provided).
        name: Collection name.
        embedding_function: Embedding function for vector search.
        workspace_id: Workspace identifier (new).

    Returns:
        SeekDB Collection instance.
    """
    client = get_seekdb_client(thread_id, workspace_id)
    from pyseekdb import Configuration, FulltextParserConfig, HNSWConfiguration

    fulltext = FulltextParserConfig(parser=settings.SEEKDB_FULLTEXT_PARSER)
    if embedding_function is None:
        configuration = Configuration(fulltext_config=fulltext)
    else:
        configuration = Configuration(
            hnsw=HNSWConfiguration(
                dimension=embedding_function.dimension,
                distance=settings.SEEKDB_DISTANCE_METRIC,
            ),
            fulltext_config=fulltext,
        )
    return client.create_collection(
        name=name,
        configuration=configuration,
        embedding_function=embedding_function,
    )
