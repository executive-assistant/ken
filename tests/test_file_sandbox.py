"""Unit tests for file sandbox with thread_id separation."""

from pathlib import Path
from unittest.mock import patch

import pytest

from cassey.storage.file_sandbox import (
    FileSandbox,
    set_thread_id,
    get_thread_id,
    read_file,
    write_file,
    list_files,
)


class TestThreadIdContext:
    """Test thread_id context variable."""

    def test_set_and_get_thread_id(self):
        """Test setting and getting thread_id from context."""
        # Initially None
        assert get_thread_id() is None

        # Set and get
        set_thread_id("test_thread")
        assert get_thread_id() == "test_thread"

        # Reset to None for other tests
        set_thread_id("")

    def test_context_isolation(self):
        """Test that context variable is isolated per task."""
        set_thread_id("thread_1")
        assert get_thread_id() == "thread_1"

        # Setting new value overrides
        set_thread_id("thread_2")
        assert get_thread_id() == "thread_2"

        # Reset
        set_thread_id("")


class TestSandboxWithThreadId:
    """Test FileSandbox with thread_id separation."""

    @pytest.fixture
    def temp_root(self, tmp_path):
        """Create a temporary root for testing."""
        return tmp_path / "files"

    @pytest.fixture
    def sandbox(self, temp_root):
        """Create a sandbox with temporary root."""
        with patch("cassey.storage.file_sandbox.settings.FILES_ROOT", temp_root):
            with patch("cassey.storage.file_sandbox.settings.ALLOWED_FILE_EXTENSIONS", {".txt", ".md"}):
                with patch("cassey.storage.file_sandbox.settings.MAX_FILE_SIZE_MB", 10):
                    return FileSandbox(root=temp_root)

    def test_sandbox_defaults_to_global(self, temp_root):
        """Test that without thread_id, sandbox uses global root."""
        with patch("cassey.storage.file_sandbox.settings.FILES_ROOT", temp_root):
            with patch("cassey.storage.file_sandbox.get_thread_id", return_value=None):
                from cassey.storage.file_sandbox import get_sandbox
                sandbox = get_sandbox()
                assert sandbox.root == temp_root

    def test_sandbox_with_thread_id(self, temp_root):
        """Test that thread_id creates separate directory."""
        # Set thread_id
        set_thread_id("telegram:user123")

        with patch("cassey.storage.file_sandbox.settings.FILES_ROOT", temp_root):
            with patch("cassey.storage.file_sandbox.settings.ALLOWED_FILE_EXTENSIONS", {".txt", ".md"}):
                with patch("cassey.storage.file_sandbox.settings.MAX_FILE_SIZE_MB", 10):
                    sandbox = get_sandbox()

        # Should create thread-specific directory
        expected_path = temp_root / "telegram_user123"
        assert sandbox.root == expected_path

        # Reset
        set_thread_id("")

    def test_sandbox_sanitizes_thread_id(self, temp_root):
        """Test that thread_id is sanitized for directory names."""
        set_thread_id("http:user:with:colons/and/slashes")

        with patch("cassey.storage.file_sandbox.settings.FILES_ROOT", temp_root):
            with patch("cassey.storage.file_sandbox.settings.ALLOWED_FILE_EXTENSIONS", {".txt", ".md"}):
                with patch("cassey.storage.file_sandbox.settings.MAX_FILE_SIZE_MB", 10):
                    sandbox = get_sandbox()

        # Should replace : and / with _
        expected_path = temp_root / "http_user_with_colons_and_slashes"
        assert sandbox.root == expected_path

        # Reset
        set_thread_id("")

    def test_sandbox_user_id_takes_priority(self, temp_root):
        """Test that explicit user_id takes priority over thread_id context."""
        set_thread_id("http:thread1")

        with patch("cassey.storage.file_sandbox.settings.FILES_ROOT", temp_root):
            with patch("cassey.storage.file_sandbox.settings.ALLOWED_FILE_EXTENSIONS", {".txt", ".md"}):
                with patch("cassey.storage.file_sandbox.settings.MAX_FILE_SIZE_MB", 10):
                    # Explicit user_id should take priority
                    sandbox = get_sandbox(user_id="explicit_user")

        # Should use explicit user_id
        expected_path = temp_root / "explicit_user"
        assert sandbox.root == expected_path

        # Reset
        set_thread_id("")


class TestFileOperationsWithThreadId:
    """Test file operations with thread_id separation."""

    @pytest.fixture
    def temp_root(self, tmp_path):
        """Create a temporary root for testing."""
        return tmp_path / "files"

    def test_write_read_with_thread_id(self, temp_root):
        """Test writing and reading files with thread_id isolation."""
        # Thread 1 writes
        set_thread_id("telegram:user1")
        with patch("cassey.storage.file_sandbox.settings.FILES_ROOT", temp_root):
            with patch("cassey.storage.file_sandbox.settings.ALLOWED_FILE_EXTENSIONS", {".txt"}):
                with patch("cassey.storage.file_sandbox.settings.MAX_FILE_SIZE_MB", 10):
                    result = write_file("test.txt", "Hello from user1")
                    assert "File written" in result

        # Thread 1 reads
        set_thread_id("telegram:user1")
        with patch("cassey.storage.file_sandbox.settings.FILES_ROOT", temp_root):
            with patch("cassey.storage.file_sandbox.settings.ALLOWED_FILE_EXTENSIONS", {".txt"}):
                with patch("cassey.storage.file_sandbox.settings.MAX_FILE_SIZE_MB", 10):
                    content = read_file("test.txt")
                    assert content == "Hello from user1"

        # Thread 2 shouldn't see thread 1's file
        set_thread_id("telegram:user2")
        with patch("cassey.storage.file_sandbox.settings.FILES_ROOT", temp_root):
            with patch("cassey.storage.file_sandbox.settings.ALLOWED_FILE_EXTENSIONS", {".txt"}):
                with patch("cassey.storage.file_sandbox.settings.MAX_FILE_SIZE_MB", 10):
                    content = read_file("test.txt")
                    assert "not found" in content.lower()

        # Reset
        set_thread_id("")

    def test_list_files_with_thread_id(self, temp_root):
        """Test listing files with thread_id isolation."""
        # Thread 1 writes files
        set_thread_id("http:thread1")
        with patch("cassey.storage.file_sandbox.settings.FILES_ROOT", temp_root):
            with patch("cassey.storage.file_sandbox.settings.ALLOWED_FILE_EXTENSIONS", {".txt", ".md"}):
                with patch("cassey.storage.file_sandbox.settings.MAX_FILE_SIZE_MB", 10):
                    write_file("a.txt", "content a")
                    write_file("b.md", "content b")

        # Thread 1 lists
        set_thread_id("http:thread1")
        with patch("cassey.storage.file_sandbox.settings.FILES_ROOT", temp_root):
            with patch("cassey.storage.file_sandbox.settings.ALLOWED_FILE_EXTENSIONS", {".txt", ".md"}):
                with patch("cassey.storage.file_sandbox.settings.MAX_FILE_SIZE_MB", 10):
                    result = list_files()
                    assert "a.txt" in result
                    assert "b.md" in result

        # Thread 2 lists (should be empty)
        set_thread_id("http:thread2")
        with patch("cassey.storage.file_sandbox.settings.FILES_ROOT", temp_root):
            with patch("cassey.storage.file_sandbox.settings.ALLOWED_FILE_EXTENSIONS", {".txt", ".md"}):
                with patch("cassey.storage.file_sandbox.settings.MAX_FILE_SIZE_MB", 10):
                    result = list_files()
                    # Should only show directory header, no files
                    assert "a.txt" not in result
                    assert "b.md" not in result

        # Reset
        set_thread_id("")
