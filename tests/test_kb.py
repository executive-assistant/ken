"""Unit tests for SeekDB-based KB tools."""

import json

import pytest

from cassey.config import settings
from cassey.storage.file_sandbox import set_thread_id
from cassey.storage import kb_tools


def _skip_if_seekdb_unavailable():
    try:
        from pyseekdb.client.client_seekdb_embedded import _PYLIBSEEKDB_AVAILABLE
    except Exception:
        pytest.skip("pyseekdb not available")
    if not _PYLIBSEEKDB_AVAILABLE:
        pytest.skip("SeekDB embedded is Linux-only; skipping on this platform")


@pytest.fixture(autouse=True)
def _seekdb_guard():
    _skip_if_seekdb_unavailable()


@pytest.fixture
def thread_context(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "USERS_ROOT", tmp_path / "users")
    monkeypatch.setattr(settings, "SEEKDB_EMBEDDING_MODE", "none")
    set_thread_id("telegram:test_seekdb")
    yield
    set_thread_id("")


def test_create_and_list_kb(thread_context):
    docs = json.dumps([
        {"content": "First document", "metadata": {"tag": "a"}},
        {"content": "Second document", "metadata": {"tag": "b"}},
    ])
    result = kb_tools.create_kb_collection.invoke({"collection_name": "notes", "documents": docs})
    assert "Created KB collection 'notes'" in result

    listing = kb_tools.kb_list.invoke({})
    assert "notes" in listing


def test_search_kb(thread_context):
    docs = json.dumps([
        {"content": "SeekDB supports hybrid search"},
        {"content": "DuckDB is different"},
    ])
    kb_tools.create_kb_collection.invoke({"collection_name": "docs", "documents": docs})

    result = kb_tools.search_kb.invoke({"query": "hybrid", "collection_name": "docs", "limit": 5})
    assert "Search results" in result
    assert "hybrid" in result.lower()


def test_describe_and_delete(thread_context):
    docs = json.dumps([
        {"content": "Describe me"},
    ])
    kb_tools.create_kb_collection.invoke({"collection_name": "tmp", "documents": docs})

    describe = kb_tools.describe_kb_collection.invoke({"collection_name": "tmp"})
    assert "Collection 'tmp'" in describe

    delete = kb_tools.drop_kb_collection.invoke({"collection_name": "tmp"})
    assert "Deleted KB collection 'tmp'" in delete
