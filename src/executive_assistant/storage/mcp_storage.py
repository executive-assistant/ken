"""MCP server configuration storage and loader (admin-only).

This module provides storage for admin-defined MCP server configurations.
The structure mirrors user MCP storage for consistency:

    data/admins/mcp/
    ├── mcp.json           # Local (stdio) servers
    ├── mcp_remote.json    # Remote (HTTP/SSE) servers
    └── backups/           # Configuration backups
"""

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from executive_assistant.config import settings


def _utc_now() -> str:
    """Get current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def get_admin_mcp_dir() -> Path:
    """Get admin MCP directory path.

    Returns:
        Path to admin MCP directory: data/admins/mcp/
    """
    mcp_dir = settings.ADMINS_ROOT / "mcp"
    mcp_dir.mkdir(parents=True, exist_ok=True)
    return mcp_dir


def get_admin_mcp_config_path() -> Path:
    """Get admin MCP local config path.

    Returns:
        Path to mcp.json: data/admins/mcp/mcp.json
    """
    return get_admin_mcp_dir() / "mcp.json"


def get_admin_mcp_remote_config_path() -> Path:
    """Get admin MCP remote config path.

    Returns:
        Path to mcp_remote.json: data/admins/mcp/mcp_remote.json
    """
    return get_admin_mcp_dir() / "mcp_remote.json"


def _check_legacy_config() -> Path | None:
    """Check for legacy mcp.json at admin root and migrate if needed.

    Returns:
        Path to legacy config if it exists, None otherwise.
    """
    legacy_path = settings.ADMINS_ROOT / "mcp.json"
    if legacy_path.exists():
        # Migrate to new location
        new_path = get_admin_mcp_config_path()
        new_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(legacy_path, new_path)
        # Create backup of old file
        backup_path = legacy_path.with_suffix(".json.migrated")
        shutil.copy2(legacy_path, backup_path)
        legacy_path.unlink()
        return new_path
    return None


def load_mcp_config() -> dict[str, Any]:
    """Load admin MCP configuration (local/stdio servers).

    Checks for legacy config location and migrates if found.

    Returns:
        MCP configuration dict with 'mcpServers', 'mcpEnabled', and 'loadMcpTools'.
    """
    # Check for legacy config
    _check_legacy_config()

    config_path = get_admin_mcp_config_path()
    if not config_path.exists():
        return {
            "version": "1.0",
            "updated_at": _utc_now(),
            "mcpServers": {},
            "mcpEnabled": False,
            "loadMcpTools": "default"
        }

    try:
        with open(config_path) as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in admin mcp.json: {e}")

    config.setdefault("version", "1.0")
    config.setdefault("updated_at", _utc_now())
    config.setdefault("mcpServers", {})
    config.setdefault("mcpEnabled", False)
    config.setdefault("loadMcpTools", "default")
    return config


def save_admin_mcp_config(config: dict) -> None:
    """Save admin MCP configuration (local/stdio servers).

    Args:
        config: MCP configuration dict to save.
    """
    config_path = get_admin_mcp_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Update timestamp
    config["updated_at"] = _utc_now()

    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)


def load_admin_mcp_remote_config() -> dict[str, Any]:
    """Load admin MCP remote configuration (HTTP/SSE servers).

    Returns:
        MCP configuration dict with 'mcpServers' for remote servers.
    """
    config_path = get_admin_mcp_remote_config_path()
    if not config_path.exists():
        return {
            "version": "1.0",
            "updated_at": _utc_now(),
            "mcpServers": {},
        }

    try:
        with open(config_path) as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in admin mcp_remote.json: {e}")

    config.setdefault("version", "1.0")
    config.setdefault("updated_at", _utc_now())
    config.setdefault("mcpServers", {})
    return config


def save_admin_mcp_remote_config(config: dict) -> None:
    """Save admin MCP remote configuration (HTTP/SSE servers).

    Args:
        config: MCP configuration dict for remote servers.
    """
    config_path = get_admin_mcp_remote_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Update timestamp
    config["updated_at"] = _utc_now()

    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)


def delete_admin_mcp_config() -> None:
    """Delete admin MCP configuration (removes both local and remote config files)."""
    local_path = get_admin_mcp_config_path()
    remote_path = get_admin_mcp_remote_config_path()

    if local_path.exists():
        local_path.unlink()
    if remote_path.exists():
        remote_path.unlink()


def get_admin_mcp_backups_dir() -> Path:
    """Get admin MCP backups directory.

    Returns:
        Path to backups directory: data/admins/mcp/backups/
    """
    backups_dir = get_admin_mcp_dir() / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)
    return backups_dir


def backup_admin_mcp_config(config_type: str = "local") -> Path:
    """Create a backup of admin MCP configuration.

    Args:
        config_type: Either 'local' or 'remote'

    Returns:
        Path to the backup file created.
    """
    backups_dir = get_admin_mcp_backups_dir()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    if config_type == "local":
        source_path = get_admin_mcp_config_path()
        backup_name = f"mcp.json.backup_{timestamp}"
    else:  # remote
        source_path = get_admin_mcp_remote_config_path()
        backup_name = f"mcp_remote.json.backup_{timestamp}"

    backup_path = backups_dir / backup_name
    if source_path.exists():
        shutil.copy2(source_path, backup_path)

    return backup_path


def list_admin_mcp_backups(config_type: str = "local") -> list[dict]:
    """List available admin MCP configuration backups.

    Args:
        config_type: Either 'local' or 'remote'

    Returns:
        List of backup info dicts with 'filename', 'timestamp', 'size'.
    """
    backups_dir = get_admin_mcp_backups_dir()
    prefix = "mcp.json.backup_" if config_type == "local" else "mcp_remote.json.backup_"

    backups = []
    for backup_file in backups_dir.glob(f"{prefix}*"):
        try:
            stat = backup_file.stat()
            # Extract timestamp from filename
            timestamp_str = backup_file.stem.split("_")[-1]
            backups.append({
                "filename": backup_file.name,
                "timestamp": timestamp_str,
                "size": stat.st_size,
                "path": backup_file
            })
        except Exception:
            continue

    return sorted(backups, key=lambda x: x["timestamp"], reverse=True)
