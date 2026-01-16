"""
Workspace-based storage routing.

This module provides the workspace abstraction layer that routes all storage
operations (files, KB, DB, etc.) through workspace_id rather than thread_id.

Identity Resolution:
  1. Extract user_id from request context (Telegram, HTTP)
  2. Resolve aliases to canonical user_id
  3. Get or create workspace for user
  4. Route thread_id to workspace_id

Storage Layout:
  data/workspaces/{workspace_id}/
    files/
    kb/
    db/
    mem/
    reminders/
    workflows/
"""

import asyncio
import uuid
from contextvars import ContextVar
from functools import lru_cache
from pathlib import Path
from typing import Literal

import asyncpg

from cassey.config.settings import settings


# Context variable for workspace_id - set by channels when processing messages
_workspace_id: ContextVar[str | None] = ContextVar("_workspace_id", default=None)

# Cache for workspace lookups (within a single request/transaction)
_workspace_cache: dict[str, dict] = {}


def set_workspace_id(workspace_id: str) -> None:
    """Set the workspace_id for the current context."""
    _workspace_id.set(workspace_id)


def get_workspace_id() -> str | None:
    """Get the workspace_id for the current context."""
    return _workspace_id.get()


def clear_workspace_id() -> None:
    """Clear the workspace_id from the current context."""
    try:
        _workspace_id.set(None)
    except Exception:
        pass


def sanitize_thread_id(thread_id: str) -> str:
    """
    Sanitize thread_id for use as filename/directory name.

    Replaces characters that could cause issues in filenames.

    Args:
        thread_id: Raw thread_id (e.g., "telegram:user123", "email:user@example.com")

    Returns:
        Sanitized string safe for filenames (e.g., "telegram_user123", "email_user_example.com")
    """
    replacements = {
        ":": "_",
        "/": "_",
        "@": "_",
        "\\": "_",
    }
    for old, new in replacements.items():
        thread_id = thread_id.replace(old, new)
    return thread_id


def generate_workspace_id() -> str:
    """Generate a new unique workspace ID."""
    return f"ws:{uuid.uuid4()}"


def generate_group_id() -> str:
    """Generate a new unique group ID."""
    return f"group:{uuid.uuid4()}"


def generate_anon_user_id() -> str:
    """Generate a new anonymous user ID for web guests."""
    return f"anon:{uuid.uuid4()}"


# ============================================================================
# Workspace Path Resolution
# ============================================================================

def get_workspaces_root() -> Path:
    """Get the root directory for all workspaces."""
    root = Path("./data/workspaces").resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def get_workspace_path(workspace_id: str) -> Path:
    """
    Get the root directory for a specific workspace.

    Args:
        workspace_id: The workspace ID

    Returns:
        Path to workspace root: data/workspaces/{workspace_id}/
    """
    sanitized = sanitize_thread_id(workspace_id)
    workspace_path = get_workspaces_root() / sanitized
    workspace_path.mkdir(parents=True, exist_ok=True)
    return workspace_path


def get_workspace_files_path(workspace_id: str) -> Path:
    """Get the files directory for a workspace."""
    return get_workspace_path(workspace_id) / "files"


def get_workspace_kb_path(workspace_id: str) -> Path:
    """Get the KB directory for a workspace."""
    return get_workspace_path(workspace_id) / "kb"


def get_workspace_db_path(workspace_id: str) -> Path:
    """Get the DB directory for a workspace."""
    db_path = get_workspace_path(workspace_id) / "db"
    db_path.mkdir(parents=True, exist_ok=True)
    return db_path / "db.db"


def get_workspace_mem_path(workspace_id: str) -> Path:
    """Get the memory directory for a workspace."""
    mem_path = get_workspace_path(workspace_id) / "mem"
    mem_path.mkdir(parents=True, exist_ok=True)
    return mem_path / "mem.db"


def get_workspace_reminders_path(workspace_id: str) -> Path:
    """Get the reminders directory for a workspace."""
    return get_workspace_path(workspace_id) / "reminders"


def get_workspace_workflows_path(workspace_id: str) -> Path:
    """Get the workflows directory for a workspace."""
    return get_workspace_path(workspace_id) / "workflows"


# ============================================================================
# Database Operations (PostgreSQL)
# ============================================================================

async def get_db_conn() -> asyncpg.Connection:
    """Get a database connection."""
    return await asyncpg.connect(settings.POSTGRES_URL)


async def resolve_user_id(user_id: str, conn: asyncpg.Connection | None = None) -> str:
    """
    Resolve a user_id to its canonical form, handling aliases.

    Args:
        user_id: The user ID (may be an alias)
        conn: Optional database connection

    Returns:
        The canonical user_id
    """
    if conn is None:
        conn = await get_db_conn()

    # Check if user_id is an alias
    canonical = await conn.fetchval(
        "SELECT user_id FROM user_aliases WHERE alias_id = $1",
        user_id
    )

    return canonical or user_id


async def get_user_workspace(user_id: str, conn: asyncpg.Connection | None = None) -> str | None:
    """
    Get the workspace_id for a user (individual workspace).

    Args:
        user_id: The canonical user_id
        conn: Optional database connection

    Returns:
        The workspace_id or None if user has no workspace
    """
    if conn is None:
        conn = await get_db_conn()

    return await conn.fetchval(
        "SELECT workspace_id FROM user_workspaces WHERE user_id = $1",
        user_id
    )


async def get_thread_workspace(thread_id: str, conn: asyncpg.Connection | None = None) -> str | None:
    """
    Get the workspace_id for a thread.

    Args:
        thread_id: The thread ID
        conn: Optional database connection

    Returns:
        The workspace_id or None if thread has no workspace
    """
    if conn is None:
        conn = await get_db_conn()

    return await conn.fetchval(
        "SELECT workspace_id FROM thread_workspaces WHERE thread_id = $1",
        thread_id
    )


async def ensure_user(
    user_id: str,
    conn: asyncpg.Connection | None = None,
) -> str:
    """
    Ensure a user exists, creating if necessary.

    Args:
        user_id: The user ID (should be canonical, not an alias)
        conn: Optional database connection

    Returns:
        The user_id
    """
    if conn is None:
        conn = await get_db_conn()

    await conn.execute(
        "INSERT INTO users (user_id) VALUES ($1) ON CONFLICT DO NOTHING",
        user_id
    )
    return user_id


async def ensure_user_workspace(
    user_id: str,
    conn: asyncpg.Connection | None = None,
) -> str:
    """
    Ensure a user has an individual workspace, creating if necessary.

    Args:
        user_id: The canonical user_id
        conn: Optional database connection

    Returns:
        The workspace_id
    """
    if conn is None:
        conn = await get_db_conn()

    # First ensure user exists
    await ensure_user(user_id, conn)

    # Check if workspace exists
    existing = await get_user_workspace(user_id, conn)
    if existing:
        return existing

    # Create new workspace
    workspace_id = generate_workspace_id()

    async with conn.transaction():
        # Create workspace
        await conn.execute(
            """INSERT INTO workspaces (workspace_id, type, name, owner_user_id)
               VALUES ($1, 'individual', 'My Workspace', $2)""",
            workspace_id, user_id
        )

        # Map user to workspace
        await conn.execute(
            "INSERT INTO user_workspaces (user_id, workspace_id) VALUES ($1, $2)",
            user_id, workspace_id
        )

    return workspace_id


async def ensure_thread_workspace(
    thread_id: str,
    user_id: str,
    conn: asyncpg.Connection | None = None,
) -> str:
    """
    Ensure a thread has a workspace, creating if necessary.

    This resolves the user to their canonical form (via aliases),
    ensures they have a workspace, and maps the thread to it.

    Args:
        thread_id: The thread ID
        user_id: The user ID from request (may be an alias)
        conn: Optional database connection

    Returns:
        The workspace_id
    """
    if conn is None:
        conn = await get_db_conn()

    # Resolve alias to canonical user_id
    canonical_user_id = await resolve_user_id(user_id, conn)

    # Ensure user has workspace
    workspace_id = await ensure_user_workspace(canonical_user_id, conn)

    # Map thread to workspace
    await conn.execute(
        """INSERT INTO thread_workspaces (thread_id, workspace_id)
           VALUES ($1, $2)
           ON CONFLICT (thread_id) DO UPDATE SET workspace_id = $2""",
        thread_id, workspace_id
    )

    return workspace_id


async def get_workspace_info(workspace_id: str, conn: asyncpg.Connection | None = None) -> dict | None:
    """
    Get workspace information.

    Args:
        workspace_id: The workspace ID
        conn: Optional database connection

    Returns:
        Workspace info dict or None
    """
    if conn is None:
        conn = await get_db_conn()

    row = await conn.fetchrow(
        """SELECT workspace_id, type, name, owner_user_id, owner_group_id, owner_system_id, created_at
           FROM workspaces WHERE workspace_id = $1""",
        workspace_id
    )

    if not row:
        return None

    return {
        "workspace_id": row["workspace_id"],
        "type": row["type"],
        "name": row["name"],
        "owner_user_id": row["owner_user_id"],
        "owner_group_id": row["owner_group_id"],
        "owner_system_id": row["owner_system_id"],
        "created_at": row["created_at"],
    }


# ============================================================================
# Access Control
# ============================================================================

ROLE_PERMISSIONS = {
    "admin": {"read": True, "write": True, "admin": True},
    "editor": {"read": True, "write": True, "admin": False},
    "reader": {"read": True, "write": False, "admin": False}
}


async def can_access(
    user_id: str,
    workspace_id: str,
    action: Literal["read", "write", "admin"],
    conn: asyncpg.Connection | None = None,
) -> bool:
    """
    Check if a user can perform an action on a workspace.

    Args:
        user_id: The user ID
        workspace_id: The workspace ID
        action: The action to check (read, write, admin)
        conn: Optional database connection

    Returns:
        True if access is granted, False otherwise
    """
    if conn is None:
        conn = await get_db_conn()

    # Resolve alias to canonical user_id
    canonical_user_id = await resolve_user_id(user_id, conn)

    # Get workspace info
    workspace = await get_workspace_info(workspace_id, conn)
    if not workspace:
        return False

    # Workspace owner is always admin
    if workspace["owner_user_id"] == canonical_user_id:
        return True

    # Check explicit workspace membership
    member = await conn.fetchrow(
        """SELECT role FROM workspace_members
           WHERE workspace_id = $1 AND user_id = $2""",
        workspace_id, canonical_user_id
    )
    if member:
        return ROLE_PERMISSIONS[member["role"]].get(action, False)

    # Group workspace: check group membership
    if workspace["owner_group_id"]:
        group_role = await conn.fetchval(
            """SELECT role FROM group_members
               WHERE group_id = $1 AND user_id = $2""",
            workspace["owner_group_id"], canonical_user_id
        )
        if group_role:
            # Group admins are workspace admins, members are readers
            return group_role == "admin" or action == "read"

    # Public workspace: everyone can read
    if workspace["type"] == "public" and action == "read":
        return True

    # Check ACL for external grants
    acl_grant = await conn.fetchval(
        """SELECT permission FROM workspace_acl
           WHERE workspace_id = $1
           AND ($2 = 'read' OR permission = 'write' OR permission = 'admin')
           AND target_user_id = $3
           AND (expires_at IS NULL OR expires_at > NOW())
           ORDER BY
             CASE permission
               WHEN 'admin' THEN 3
               WHEN 'write' THEN 2
               WHEN 'read' THEN 1
               ELSE 0
             END DESC
           LIMIT 1""",
        workspace_id, action, canonical_user_id
    )

    if acl_grant:
        if acl_grant == "admin":
            return True
        if acl_grant == "write" and action in ("read", "write"):
            return True
        if acl_grant == "read" and action == "read":
            return True

    return False


# ============================================================================
# Accessible Workspaces
# ============================================================================

async def accessible_workspaces(
    user_id: str,
    conn: asyncpg.Connection | None = None,
) -> list[dict]:
    """
    Return all workspaces the user can access.

    Args:
        user_id: The user ID
        conn: Optional database connection

    Returns:
        List of workspace dicts with role and type info
    """
    if conn is None:
        conn = await get_db_conn()

    # Resolve alias to canonical user_id
    canonical_user_id = await resolve_user_id(user_id, conn)

    results = []

    # 1. Individual workspace (if owner)
    own = await conn.fetchrow(
        """SELECT w.workspace_id, w.type, w.name
           FROM user_workspaces uw
           JOIN workspaces w ON w.workspace_id = uw.workspace_id
           WHERE uw.user_id = $1""",
        canonical_user_id
    )
    if own:
        results.append({
            "workspace_id": own["workspace_id"],
            "role": "admin",
            "type": own["type"],
            "name": own["name"],
        })

    # 2. Group workspaces (via group membership)
    group_rows = await conn.fetch(
        """SELECT DISTINCT w.workspace_id, w.type, w.name, gm.role
           FROM group_members gm
           JOIN group_workspaces gw ON gw.group_id = gm.group_id
           JOIN workspaces w ON w.workspace_id = gw.workspace_id
           WHERE gm.user_id = $1""",
        canonical_user_id
    )
    for row in group_rows:
        role = "admin" if row["role"] == "admin" else "reader"
        results.append({
            "workspace_id": row["workspace_id"],
            "role": role,
            "type": row["type"],
            "name": row["name"],
        })

    # 3. Workspaces where user is explicit member
    member_rows = await conn.fetch(
        """SELECT w.workspace_id, w.type, w.name, wm.role
           FROM workspace_members wm
           JOIN workspaces w ON w.workspace_id = wm.workspace_id
           WHERE wm.user_id = $1""",
        canonical_user_id
    )
    for row in member_rows:
        results.append({
            "workspace_id": row["workspace_id"],
            "role": row["role"],
            "type": row["type"],
            "name": row["name"],
        })

    # 4. Public workspace (everyone has read access)
    public_ws = await conn.fetchrow(
        "SELECT workspace_id, name FROM workspaces WHERE type = 'public'"
    )
    if public_ws and not any(w["workspace_id"] == public_ws["workspace_id"] for w in results):
        results.append({
            "workspace_id": public_ws["workspace_id"],
            "role": "reader",
            "type": "public",
            "name": public_ws["name"],
        })

    return results


# ============================================================================
# Alias / Merge Operations
# ============================================================================

async def add_alias(
    alias_id: str,
    canonical_user_id: str,
    conn: asyncpg.Connection | None = None,
) -> None:
    """
    Add an alias mapping (for merges/upgrades).

    Args:
        alias_id: The alias (e.g., anon:abc123)
        canonical_user_id: The canonical user ID
        conn: Optional database connection
    """
    if conn is None:
        conn = await get_db_conn()

    await conn.execute(
        "INSERT INTO user_aliases (alias_id, user_id) VALUES ($1, $2) ON CONFLICT (alias_id) DO UPDATE SET user_id = $2",
        alias_id, canonical_user_id
    )


async def resolve_alias_chain(user_id: str, conn: asyncpg.Connection | None = None) -> str:
    """
    Resolve an alias chain to get the canonical user_id.

    Args:
        user_id: The user ID (may be an alias)
        conn: Optional database connection

    Returns:
        The canonical user_id
    """
    if conn is None:
        conn = await get_db_conn()

    seen = {user_id}
    current = user_id

    while True:
        resolved = await conn.fetchval(
            "SELECT user_id FROM user_aliases WHERE alias_id = $1",
            current
        )
        if not resolved:
            break
        if resolved in seen:
            # Circular reference detected, return the original
            break
        seen.add(resolved)
        current = resolved

    return current


# ============================================================================
# Public Workspace Setup
# ============================================================================

async def ensure_public_workspace(conn: asyncpg.Connection | None = None) -> str:
    """
    Ensure the public workspace exists, creating if necessary.

    Args:
        conn: Optional database connection

    Returns:
        The public workspace_id
    """
    if conn is None:
        conn = await get_db_conn()

    workspace_id = "public"

    row = await conn.fetchrow(
        "SELECT workspace_id FROM workspaces WHERE workspace_id = $1",
        workspace_id
    )

    if not row:
        await conn.execute(
            """INSERT INTO workspaces (workspace_id, type, name, owner_system_id)
               VALUES ($1, 'public', 'Public', 'public')""",
            workspace_id
        )

    return workspace_id
