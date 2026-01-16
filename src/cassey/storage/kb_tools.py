"""Knowledge Base tools using SeekDB (pyseekdb)."""

from __future__ import annotations

import json
from uuid import uuid4

from langchain_core.tools import tool

from cassey.config import settings
from cassey.storage.db_storage import validate_identifier
from cassey.storage.file_sandbox import get_thread_id
from cassey.storage.meta_registry import (
    record_kb_table_added,
    record_kb_table_removed,
)
from cassey.storage.seekdb_storage import (
    create_seekdb_collection,
    get_seekdb_client,
    get_seekdb_collection,
    list_seekdb_collections,
)
from cassey.storage.workspace_storage import get_workspace_id


def _get_embedding_function():
    if settings.SEEKDB_EMBEDDING_MODE == "none":
        return None
    from pyseekdb import DefaultEmbeddingFunction

    return DefaultEmbeddingFunction()


def _ensure_seekdb_available() -> str | None:
    try:
        from pyseekdb.client.client_seekdb_embedded import _PYLIBSEEKDB_AVAILABLE
    except Exception:
        return "SeekDB is not available. Install pyseekdb to use the KB."
    if not _PYLIBSEEKDB_AVAILABLE:
        return (
            "SeekDB embedded mode is unavailable (pylibseekdb is Linux-only). "
            "Run on Linux or provide a SeekDB server implementation."
        )
    return None


def _format_doc_line(doc_id: str, content: str, metadata: dict | None, score: float | None) -> str:
    meta_str = ""
    if metadata:
        meta_str = f" [metadata: {metadata}]"
    score_str = f"[{score:.2f}] " if score is not None else ""
    return f"{score_str}(id: {doc_id}) {content}{meta_str}"


def _get_storage_id() -> str:
    """
    Get the storage identifier (workspace_id or thread_id) for KB operations.

    Priority:
    1. workspace_id from context (new workspace-based routing)
    2. thread_id from context (legacy thread-based routing)

    Returns:
        The storage identifier (workspace_id or thread_id).
    """
    # Check workspace_id first
    workspace_id = get_workspace_id()
    if workspace_id:
        return workspace_id

    # Fall back to thread_id
    thread_id = get_thread_id()
    if not thread_id:
        raise ValueError("No thread_id/workspace_id in context")

    return thread_id


@tool
def create_kb_collection(collection_name: str, documents: str = "") -> str:
    """
    Create a KB collection in SeekDB.

    Args:
        collection_name: Collection name (letters/numbers/underscore).
        documents: JSON array of document objects: [{"content": "...", "metadata": {...}}]
    """
    availability_error = _ensure_seekdb_available()
    if availability_error:
        return f"Error: {availability_error}"

    validate_identifier(collection_name)

    parsed_docs: list[dict] = []
    if documents:
        try:
            parsed_docs = json.loads(documents)
        except json.JSONDecodeError as exc:
            return f"Error: Invalid JSON data - {exc}"
        if not isinstance(parsed_docs, list):
            return "Error: documents must be a JSON array"

    try:
        storage_id = _get_storage_id()
        client = get_seekdb_client(thread_id=storage_id)
        existing = {c.name for c in client.list_collections()}
        if collection_name in existing:
            client.delete_collection(collection_name)

        embedding_function = _get_embedding_function()
        collection = create_seekdb_collection(storage_id, collection_name, embedding_function)

        if parsed_docs:
            ids = [str(uuid4()) for _ in parsed_docs]
            documents_list = [doc.get("content", "") for doc in parsed_docs]
            metadatas = []
            for doc in parsed_docs:
                metadata = doc.get("metadata")
                if metadata is None:
                    metadatas.append({})
                elif isinstance(metadata, dict):
                    metadatas.append(metadata)
                else:
                    metadatas.append({"metadata": metadata})

            collection.add(ids=ids, documents=documents_list, metadatas=metadatas)

        record_kb_table_added(storage_id, collection_name)
        if parsed_docs:
            return f"Created KB collection '{collection_name}' with {len(parsed_docs)} documents"
        return f"Created KB collection '{collection_name}' (empty, ready for documents)"
    except Exception as exc:
        return f"Error creating collection: {exc}"


@tool
def search_kb(query: str, collection_name: str = "", limit: int = 5) -> str:
    """Search KB collections with full-text or hybrid search."""
    availability_error = _ensure_seekdb_available()
    if availability_error:
        return f"Error: {availability_error}"

    try:
        storage_id = _get_storage_id()
        if collection_name:
            validate_identifier(collection_name)
            tables = list_seekdb_collections(thread_id=storage_id)
            if collection_name not in tables:
                return f"Error: KB collection '{collection_name}' not found"
            tables = [collection_name]
        else:
            tables = list_seekdb_collections(thread_id=storage_id)

        if not tables:
            return "No KB collections found. Use create_kb_collection to create one first."

        results: list[str] = []
        for tbl in tables:
            try:
                collection = get_seekdb_collection(storage_id, tbl)
            except Exception:
                continue

            embedding_function = getattr(collection, "embedding_function", None)
            if embedding_function is not None:
                response = collection.hybrid_search(
                    query={"where_document": {"$contains": query}},
                    knn={"query_texts": [query], "n_results": limit},
                    rank={"rrf": {}},
                    n_results=limit,
                    include=["documents", "metadatas"],
                )
                ids = response.get("ids", [[]])[0]
                docs = response.get("documents", [[]])[0]
                metas = response.get("metadatas", [[]])[0]
                scores = response.get("scores") or response.get("distances")
                if scores:
                    scores = scores[0]
            else:
                response = collection.get(
                    where_document={"$contains": query},
                    limit=limit,
                    include=["documents", "metadatas"],
                )
                ids = response.get("ids", [])
                docs = response.get("documents", [])
                metas = response.get("metadatas", [])
                scores = None

            if ids:
                header = f"--- From '{tbl}' ---"
                results.append(header)
                for idx, doc_id in enumerate(ids):
                    score = scores[idx] if scores is not None and idx < len(scores) else None
                    metadata = metas[idx] if idx < len(metas) else {}
                    content = docs[idx] if idx < len(docs) else ""
                    results.append(_format_doc_line(str(doc_id), content, metadata, score))

        if not results:
            if collection_name:
                return f"No matches found in '{collection_name}' for query: {query}"
            return f"No matches found across all KB collections for query: {query}"

        return f"Search results for '{query}':\n\n" + "\n".join(results)

    except Exception as exc:
        return f"Error searching KB: {exc}"


@tool
def kb_list() -> str:
    """List all KB collections with document counts."""
    availability_error = _ensure_seekdb_available()
    if availability_error:
        return f"Error: {availability_error}"

    try:
        client = get_seekdb_client()
        collections = client.list_collections()
        if not collections:
            return "Knowledge Base is empty. Use create_kb_collection to create a collection."

        lines = ["Knowledge Base collections:"]
        for collection in collections:
            try:
                count = collection.count()
            except Exception:
                count = 0
            lines.append(f"- {collection.name}: {count} documents (SeekDB)")
        return "\n".join(lines)
    except Exception as exc:
        return f"Error listing KB collections: {exc}"


@tool
def describe_kb_collection(collection_name: str) -> str:
    """Describe a KB collection and preview sample documents."""
    availability_error = _ensure_seekdb_available()
    if availability_error:
        return f"Error: {availability_error}"

    try:
        storage_id = _get_storage_id()
        validate_identifier(collection_name)
        collection = get_seekdb_collection(storage_id, collection_name)
        count = collection.count()
        preview = collection.peek(limit=3)

        lines = [f"Collection '{collection_name}':"]
        lines.append(f"Total documents: {count}")
        dimension = getattr(collection, "dimension", None)
        if dimension:
            lines.append(f"Vector dimension: {dimension}")
        distance = getattr(collection, "distance", None)
        if distance:
            lines.append(f"Distance metric: {distance}")

        ids = preview.get("ids", [])
        docs = preview.get("documents", [])
        metas = preview.get("metadatas", [])

        if ids:
            lines.append("\nSample documents:")
            for idx, doc_id in enumerate(ids):
                metadata = metas[idx] if idx < len(metas) else {}
                content = docs[idx] if idx < len(docs) else ""
                lines.append(_format_doc_line(str(doc_id), content, metadata, None))

        return "\n".join(lines)
    except Exception as exc:
        return f"Error describing collection: {exc}"


@tool
def drop_kb_collection(collection_name: str) -> str:
    """Drop a KB collection."""
    availability_error = _ensure_seekdb_available()
    if availability_error:
        return f"Error: {availability_error}"

    try:
        storage_id = _get_storage_id()
        validate_identifier(collection_name)
        collection = get_seekdb_collection(storage_id, collection_name)
        count = collection.count()
        client = get_seekdb_client(thread_id=storage_id)
        client.delete_collection(collection_name)
        record_kb_table_removed(storage_id, collection_name)
        return f"Deleted KB collection '{collection_name}' ({count} documents removed)"
    except Exception as exc:
        return f"Error dropping collection: {exc}"


@tool
def delete_kb_documents(collection_name: str, ids: str) -> str:
    """Delete documents by ID from a collection."""
    availability_error = _ensure_seekdb_available()
    if availability_error:
        return f"Error: {availability_error}"

    validate_identifier(collection_name)
    id_list = [item.strip() for item in ids.split(",") if item.strip()]
    if not id_list:
        return "Error: No valid IDs provided"

    try:
        storage_id = _get_storage_id()
        collection = get_seekdb_collection(storage_id, collection_name)
        collection.delete(ids=id_list)
        record_kb_table_added(storage_id, collection_name)
        return f"Deleted {len(id_list)} document(s) from KB collection '{collection_name}'"
    except Exception as exc:
        return f"Error deleting documents: {exc}"


@tool
def add_kb_documents(collection_name: str, documents: str) -> str:
    """Add documents to an existing KB collection."""
    availability_error = _ensure_seekdb_available()
    if availability_error:
        return f"Error: {availability_error}"

    validate_identifier(collection_name)
    try:
        parsed_docs = json.loads(documents)
    except json.JSONDecodeError as exc:
        return f"Error: Invalid JSON data - {exc}"

    if not isinstance(parsed_docs, list):
        return "Error: documents must be a JSON array"
    if not parsed_docs:
        return "Error: documents array is empty"

    try:
        storage_id = _get_storage_id()
        collection = get_seekdb_collection(storage_id, collection_name)
        ids = [str(uuid4()) for _ in parsed_docs]
        documents_list = [doc.get("content", "") for doc in parsed_docs]
        metadatas = []
        for doc in parsed_docs:
            metadata = doc.get("metadata")
            if metadata is None:
                metadatas.append({})
            elif isinstance(metadata, dict):
                metadatas.append(metadata)
            else:
                metadatas.append({"metadata": metadata})

        collection.add(ids=ids, documents=documents_list, metadatas=metadatas)
        record_kb_table_added(storage_id, collection_name)
        return f"Added {len(parsed_docs)} documents to KB collection '{collection_name}'"
    except Exception as exc:
        return f"Error adding documents: {exc}"


async def get_kb_tools() -> list:
    """Get all Knowledge Base tools for use in the agent."""
    return [
        create_kb_collection,
        search_kb,
        kb_list,
        describe_kb_collection,
        drop_kb_collection,
        add_kb_documents,
        delete_kb_documents,
    ]
