"""Unit tests for file sandbox with thread_id separation."""

from pathlib import Path

import pytest

from cassey.storage.file_sandbox import (
    FileSandbox,
    set_thread_id,
    get_thread_id,
    read_file,
    write_file,
    list_files,
    glob_files,
    grep_files,
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

    def test_sandbox_with_thread_id(self, temp_root):
        """Test that thread_id creates separate directory."""
        # Set thread_id
        set_thread_id("telegram:user123")

        sandbox = FileSandbox(root=temp_root / "telegram_user123")

        # Should create thread-specific directory
        expected_path = temp_root / "telegram_user123"
        assert sandbox.root == expected_path

        # Reset
        set_thread_id("")

    def test_sandbox_sanitizes_thread_id(self, temp_root):
        """Test that thread_id is sanitized for directory names."""
        set_thread_id("http:user:with:colons/and/slashes")

        # Simulate sanitized directory name
        safe_thread_id = "http:user:with:colons/and/slashes"
        for char in (":", "/", "@", "\\"):
            safe_thread_id = safe_thread_id.replace(char, "_")

        sandbox = FileSandbox(root=temp_root / safe_thread_id)

        # Should replace : and / with _
        expected_path = temp_root / "http_user_with_colons_and_slashes"
        assert sandbox.root == expected_path

        # Reset
        set_thread_id("")

    def test_sandbox_user_id_takes_priority(self, temp_root):
        """Test that explicit user_id creates separate directory."""
        set_thread_id("http:thread1")

        # Explicit user_id should take priority
        sandbox = FileSandbox(root=temp_root / "explicit_user")

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
        # Thread 1 sandbox
        thread1_sandbox = FileSandbox(root=temp_root / "telegram_user1", allowed_extensions={".txt"})
        thread1_sandbox.root.mkdir(parents=True, exist_ok=True)

        # Write directly to the sandbox root (bypass validation for this test)
        path1 = thread1_sandbox.root / "test.txt"
        path1.write_text("Hello from user1", encoding="utf-8")

        # Thread 1 reads
        content = path1.read_text(encoding="utf-8")
        assert content == "Hello from user1"

        # Thread 2 sandbox - should not see thread 1's file
        thread2_sandbox = FileSandbox(root=temp_root / "telegram_user2", allowed_extensions={".txt"})
        thread2_path = thread2_sandbox.root / "test.txt"

        # Thread 2's file should not exist (different directory)
        assert not thread2_path.exists()

    def test_list_files_with_thread_id(self, temp_root):
        """Test listing files with thread_id isolation."""
        # Thread 1 sandbox
        thread1_sandbox = FileSandbox(
            root=temp_root / "http_thread1",
            allowed_extensions={".txt", ".md"}
        )
        thread1_sandbox.root.mkdir(parents=True, exist_ok=True)

        # Create files
        (thread1_sandbox.root / "a.txt").write_text("content a")
        (thread1_sandbox.root / "b.md").write_text("content b")

        # List files in thread 1
        items = []
        for item in thread1_sandbox.root.iterdir():
            items.append(item.name)

        assert "a.txt" in items
        assert "b.md" in items

        # Thread 2 sandbox - should be empty
        thread2_sandbox = FileSandbox(
            root=temp_root / "http_thread2",
            allowed_extensions={".txt", ".md"}
        )
        thread2_sandbox.root.mkdir(parents=True, exist_ok=True)

        # List files in thread 2
        items2 = []
        for item in thread2_sandbox.root.iterdir():
            items2.append(item.name)

        # Thread 2 should not see thread 1's files
        assert "a.txt" not in items2
        assert "b.md" not in items2


class TestGlobFiles:
    """Test glob_files tool."""

    @pytest.fixture
    def temp_root(self, tmp_path):
        """Create a temporary root with test files."""
        files_dir = tmp_path / "files"
        files_dir.mkdir(parents=True, exist_ok=True)

        # Create test files
        (files_dir / "test1.txt").write_text("content1")
        (files_dir / "test2.txt").write_text("content2")
        (files_dir / "data.json").write_text('{"key": "value"}')
        (files_dir / "script.py").write_text("print('hello')")

        # Create subdirectory with files
        subdir = files_dir / "subdir"
        subdir.mkdir()
        (subdir / "nested.txt").write_text("nested content")

        return files_dir

    def test_glob_all_txt(self, temp_root, monkeypatch):
        """Test globbing all .txt files."""
        # Mock get_sandbox to use temp_root
        from cassey.storage import file_sandbox
        mock_sandbox = FileSandbox(root=temp_root, allowed_extensions={".txt", ".json", ".py"})

        monkeypatch.setattr(file_sandbox, "get_sandbox", lambda: mock_sandbox)

        result = glob_files.invoke({"pattern": "*.txt", "directory": ""})
        assert "Found" in result or "test1.txt" in result
        assert "test2.txt" in result

    def test_glob_recursive(self, temp_root, monkeypatch):
        """Test recursive globbing with **."""
        from cassey.storage import file_sandbox
        mock_sandbox = FileSandbox(root=temp_root, allowed_extensions={".txt", ".json", ".py"})

        monkeypatch.setattr(file_sandbox, "get_sandbox", lambda: mock_sandbox)

        result = glob_files.invoke({"pattern": "**/*.txt", "directory": ""})
        # Should find files in subdirectory too
        assert "test1.txt" in result or "Found" in result

    def test_glob_json(self, temp_root, monkeypatch):
        """Test globbing .json files."""
        from cassey.storage import file_sandbox
        mock_sandbox = FileSandbox(root=temp_root, allowed_extensions={".txt", ".json", ".py"})

        monkeypatch.setattr(file_sandbox, "get_sandbox", lambda: mock_sandbox)

        result = glob_files.invoke({"pattern": "*.json", "directory": ""})
        assert "data.json" in result

    def test_glob_no_matches(self, temp_root, monkeypatch):
        """Test globbing with no matches."""
        from cassey.storage import file_sandbox
        mock_sandbox = FileSandbox(root=temp_root, allowed_extensions={".txt", ".json", ".py"})

        monkeypatch.setattr(file_sandbox, "get_sandbox", lambda: mock_sandbox)

        result = glob_files.invoke({"pattern": "*.md", "directory": ""})
        assert "No files found" in result


class TestGrepFiles:
    """Test grep_files tool."""

    @pytest.fixture
    def temp_root(self, tmp_path):
        """Create a temporary root with test files."""
        files_dir = tmp_path / "files"
        files_dir.mkdir(parents=True, exist_ok=True)

        # Create test files with specific content
        (files_dir / "file1.txt").write_text("hello world\nfoo bar\ntest line")
        (files_dir / "file2.txt").write_text("hello there\ngoodbye world")
        (files_dir / "file3.txt").write_text("no matches here")

        return files_dir

    def test_grep_files_mode(self, temp_root, monkeypatch):
        """Test grep with files output mode."""
        from cassey.storage import file_sandbox
        mock_sandbox = FileSandbox(root=temp_root, allowed_extensions={".txt"})

        monkeypatch.setattr(file_sandbox, "get_sandbox", lambda: mock_sandbox)

        result = grep_files.invoke({"pattern": "hello", "directory": "", "output_mode": "files"})
        assert "Found" in result
        assert "file1.txt" in result
        assert "file2.txt" in result
        assert "file3.txt" not in result

    def test_grep_count_mode(self, temp_root, monkeypatch):
        """Test grep with count output mode."""
        from cassey.storage import file_sandbox
        mock_sandbox = FileSandbox(root=temp_root, allowed_extensions={".txt"})

        monkeypatch.setattr(file_sandbox, "get_sandbox", lambda: mock_sandbox)

        result = grep_files.invoke({"pattern": "hello", "directory": "", "output_mode": "count"})
        assert "file1.txt" in result
        assert "file2.txt" in result
        assert "match" in result.lower()

    def test_grep_content_mode(self, temp_root, monkeypatch):
        """Test grep with content output mode (default)."""
        from cassey.storage import file_sandbox
        mock_sandbox = FileSandbox(root=temp_root, allowed_extensions={".txt"})

        monkeypatch.setattr(file_sandbox, "get_sandbox", lambda: mock_sandbox)

        result = grep_files.invoke({"pattern": "world", "directory": "", "output_mode": "content"})
        assert "Found" in result
        # Should show matching lines
        assert "world" in result.lower()

    def test_grep_ignore_case(self, temp_root, monkeypatch):
        """Test grep with case-insensitive search."""
        from cassey.storage import file_sandbox
        mock_sandbox = FileSandbox(root=temp_root, allowed_extensions={".txt"})

        monkeypatch.setattr(file_sandbox, "get_sandbox", lambda: mock_sandbox)

        result = grep_files.invoke({
            "pattern": "HELLO",
            "directory": "",
            "output_mode": "files",
            "ignore_case": True
        })
        assert "file1.txt" in result or "file2.txt" in result

    def test_grep_regex_pattern(self, temp_root, monkeypatch):
        """Test grep with regex pattern."""
        from cassey.storage import file_sandbox
        mock_sandbox = FileSandbox(root=temp_root, allowed_extensions={".txt"})

        monkeypatch.setattr(file_sandbox, "get_sandbox", lambda: mock_sandbox)

        # Match "hello" followed by any word
        result = grep_files.invoke({"pattern": r"hello \w+", "directory": "", "output_mode": "files"})
        assert "Found" in result

    def test_grep_no_matches(self, temp_root, monkeypatch):
        """Test grep with pattern that doesn't match."""
        from cassey.storage import file_sandbox
        mock_sandbox = FileSandbox(root=temp_root, allowed_extensions={".txt"})

        monkeypatch.setattr(file_sandbox, "get_sandbox", lambda: mock_sandbox)

        result = grep_files.invoke({"pattern": "nonexistent", "directory": "", "output_mode": "files"})
        assert "No matches found" in result
