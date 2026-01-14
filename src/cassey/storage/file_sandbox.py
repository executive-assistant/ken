"""Secure file operations within a workspace sandbox."""

import os
from contextvars import ContextVar
from pathlib import Path
from typing import Literal

from langchain_core.tools import tool

from cassey.config.settings import settings


# Context variable for thread_id - set by channels when processing messages
_thread_id: ContextVar[str | None] = ContextVar("_thread_id", default=None)


def set_thread_id(thread_id: str) -> None:
    """Set the thread_id for the current context."""
    _thread_id.set(thread_id)


def get_thread_id() -> str | None:
    """Get the thread_id for the current context."""
    return _thread_id.get()


class FileSandbox:
    """
    Secure sandbox for file operations.

    Prevents path traversal attacks and restricts file access to
    allowed extensions and size limits.

    Attributes:
        root: Root directory for file operations.
        allowed_extensions: Set of allowed file extensions.
        max_file_size_mb: Maximum file size in megabytes.
    """

    def __init__(
        self,
        root: Path | None = None,
        allowed_extensions: set[str] | None = None,
        max_file_size_mb: int | None = None,
    ) -> None:
        self.root = (root or settings.FILES_ROOT).resolve()
        self.allowed_extensions = allowed_extensions or settings.ALLOWED_FILE_EXTENSIONS
        self.max_file_size_mb = max_file_size_mb or settings.MAX_FILE_SIZE_MB
        self.max_bytes = self.max_file_size_mb * 1024 * 1024

    def _validate_path(self, path: str | Path) -> Path:
        """
        Validate and resolve a path within the sandbox.

        Args:
            path: Path to validate.

        Returns:
            Resolved absolute path within the sandbox root.

        Raises:
            SecurityError: If path traversal attempt detected.
            SecurityError: If file extension not allowed.
        """
        requested = Path(path).resolve()
        root = self.root.resolve()

        # Check for path traversal
        try:
            requested.relative_to(root)
        except ValueError:
            raise SecurityError(
                f"Path traversal blocked: {requested} is outside sandbox {root}"
            )

        # Check file extension
        if requested.suffix.lower() not in self.allowed_extensions:
            allowed = ", ".join(self.allowed_extensions)
            raise SecurityError(
                f"File type '{requested.suffix}' not allowed. Allowed types: {allowed}"
            )

        return requested

    def _validate_size(self, content: str | bytes) -> None:
        """Validate content size."""
        size = len(content.encode() if isinstance(content, str) else content)
        if size > self.max_bytes:
            raise SecurityError(
                f"File size {size} bytes exceeds limit {self.max_bytes} bytes "
                f"({self.max_file_size_mb}MB)"
            )


class SecurityError(Exception):
    """Raised when a security constraint is violated."""


# Global sandbox instance
_sandbox = FileSandbox()


def get_sandbox(user_id: str | None = None) -> FileSandbox:
    """
    Get a sandbox instance, optionally user-specific or thread-specific.

    Priority:
    1. user_id if provided (for backward compatibility)
    2. thread_id from context (set by channels)
    3. global sandbox (no separation)

    Args:
        user_id: Optional user ID for sandbox separation.

    Returns:
        A FileSandbox instance scoped to the user/thread.
    """
    if user_id:
        user_path = settings.FILES_ROOT / user_id
        user_path.mkdir(parents=True, exist_ok=True)
        return FileSandbox(root=user_path)

    # Check for thread_id in context
    thread_id_val = get_thread_id()
    if thread_id_val:
        # Sanitize thread_id for use as directory name
        # Replace colons, slashes, @, and backslashes with underscores
        safe_thread_id = thread_id_val
        for char in (":", "/", "@", "\\"):
            safe_thread_id = safe_thread_id.replace(char, "_")
        thread_path = settings.FILES_ROOT / safe_thread_id
        thread_path.mkdir(parents=True, exist_ok=True)
        return FileSandbox(root=thread_path)

    return _sandbox


@tool
def read_file(file_path: str) -> str:
    """
    Read a file from the files directory.

    Args:
        file_path: Path to the file relative to files directory.

    Returns:
        File contents as string.

    Examples:
        >>> read_file("notes.txt")
        "Hello, world!"
    """
    sandbox = get_sandbox()
    try:
        validated_path = sandbox._validate_path(file_path)
        return validated_path.read_text(encoding="utf-8")
    except SecurityError as e:
        return f"Security error: {e}"
    except FileNotFoundError:
        return f"File not found: {file_path}"
    except Exception as e:
        return f"Error reading file: {e}"


@tool
def write_file(file_path: str, content: str) -> str:
    """
    Write content to a file in the files directory.

    Args:
        file_path: Path to the file relative to files directory.
        content: Content to write.

    Returns:
        Success message or error description.

    Examples:
        >>> write_file("notes.txt", "Hello, world!")
        "File written: notes.txt"
    """
    sandbox = get_sandbox()
    try:
        sandbox._validate_size(content)
        validated_path = sandbox._validate_path(file_path)
        validated_path.parent.mkdir(parents=True, exist_ok=True)
        validated_path.write_text(content, encoding="utf-8")
        return f"File written: {file_path} ({len(content)} bytes)"
    except SecurityError as e:
        return f"Security error: {e}"
    except Exception as e:
        return f"Error writing file: {e}"


@tool
def list_files(directory: str = "") -> str:
    """
    List files in the files directory.

    Args:
        directory: Subdirectory to list (empty for root).

    Returns:
        List of files and directories.

    Examples:
        >>> list_files()
        "Files in files: notes.txt, data/"
    """
    sandbox = get_sandbox()
    try:
        target_path = sandbox.root / directory if directory else sandbox.root
        target_path = sandbox._validate_path(target_path)

        if not target_path.exists():
            return f"Directory not found: {directory}"

        items = []
        for item in target_path.iterdir():
            if item.is_dir():
                items.append(f"{item.name}/")
            else:
                items.append(item.name)

        return f"Files in {directory or 'files'}:\n" + "\n".join(sorted(items))
    except SecurityError as e:
        return f"Security error: {e}"
    except Exception as e:
        return f"Error listing files: {e}"
