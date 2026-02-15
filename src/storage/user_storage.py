from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class UserStorage:
    """
    Manages per-user storage with minimal enforcement.

    Structure:
    /data/
    └── users/
        └── {user_id}/
            ├── .auth/
            │   ├── google.json
            │   └── microsoft.json
            └── projects/               # User-managed
                ├── project_a/
                │   ├── data.db
                │   └── vectors.lance/
                └── project_b/
    """

    def __init__(
        self,
        user_id: str,
        base_path: Path | str = Path("/data"),
    ) -> None:
        self.user_id = user_id
        self.base_path = Path(base_path)
        self.user_root = self.base_path / "users" / user_id
        self.auth_dir = self.user_root / ".auth"
        self.projects_dir = self.user_root / "projects"

    def ensure_user_dir(self) -> Path:
        """Create user directory structure if it doesn't exist."""
        self.user_root.mkdir(parents=True, exist_ok=True)
        self.auth_dir.mkdir(parents=True, exist_ok=True)
        return self.user_root

    def _save_auth(self, filename: str, data: dict[str, Any]) -> Path:
        """Save authentication data to a JSON file."""
        self.ensure_user_dir()
        file_path = self.auth_dir / filename
        file_path.write_text(json.dumps(data, indent=2))
        return file_path

    def _load_auth(self, filename: str) -> dict[str, Any] | None:
        """Load authentication data from a JSON file."""
        file_path = self.auth_dir / filename
        if not file_path.exists():
            return None
        return json.loads(file_path.read_text())

    def save_google_auth(self, tokens: dict[str, Any]) -> Path:
        """Save Google OAuth tokens."""
        return self._save_auth("google.json", tokens)

    def load_google_auth(self) -> dict[str, Any] | None:
        """Load Google OAuth tokens."""
        return self._load_auth("google.json")

    def save_microsoft_auth(self, tokens: dict[str, Any]) -> Path:
        """Save Microsoft OAuth tokens."""
        return self._save_auth("microsoft.json", tokens)

    def load_microsoft_auth(self) -> dict[str, Any] | None:
        """Load Microsoft OAuth tokens."""
        return self._load_auth("microsoft.json")

    def create_sqlite(self, relative_path: str) -> Path:
        """
        Create a SQLite database at the specified relative path.

        Args:
            relative_path: Path relative to user_root (e.g., 'projects/my-project/data.db')

        Returns:
            Path to the created database file
        """
        self.ensure_user_dir()
        db_path = self.user_root / relative_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        db_path.touch()
        return db_path

    def create_lancedb(self, relative_path: str) -> Path:
        """
        Create a LanceDB database at the specified relative path.

        Args:
            relative_path: Path relative to user_root (e.g., 'projects/my-project/vectors.lance')

        Returns:
            Path to the created LanceDB directory
        """
        self.ensure_user_dir()
        lance_path = self.user_root / relative_path
        lance_path.mkdir(parents=True, exist_ok=True)
        return lance_path

    def get_project_path(self, project_name: str) -> Path:
        """Get the path to a project directory."""
        return self.projects_dir / project_name

    def get_sqlite_path(self, relative_path: str) -> Path:
        """Get the path to a SQLite database file."""
        return self.user_root / relative_path

    def get_lancedb_path(self, relative_path: str) -> Path:
        """Get the path to a LanceDB database."""
        return self.user_root / relative_path

    def list_projects(self) -> list[str]:
        """List all project directories."""
        if not self.projects_dir.exists():
            return []
        return [
            d.name for d in self.projects_dir.iterdir() if d.is_dir() and not d.name.startswith(".")
        ]

    def project_exists(self, project_name: str) -> bool:
        """Check if a project exists."""
        return self.get_project_path(project_name).exists()

    def create_project(self, project_name: str) -> Path:
        """Create a new project directory."""
        project_path = self.get_project_path(project_name)
        project_path.mkdir(parents=True, exist_ok=True)
        return project_path

    def delete_project(self, project_name: str) -> bool:
        """Delete a project directory and all its contents."""
        import shutil

        project_path = self.get_project_path(project_name)
        if project_path.exists():
            shutil.rmtree(project_path)
            return True
        return False

    def get_user_stats(self) -> dict[str, Any]:
        """Get statistics about user storage."""
        stats: dict[str, Any] = {
            "user_id": self.user_id,
            "projects": [],
            "total_size_bytes": 0,
        }

        if not self.user_root.exists():
            return stats

        projects = []
        total_size = 0

        for item in self.user_root.rglob("*"):
            if item.is_file():
                total_size += item.stat().st_size

        if self.projects_dir.exists():
            for project_dir in self.projects_dir.iterdir():
                if project_dir.is_dir() and not project_dir.name.startswith("."):
                    project_size = sum(
                        f.stat().st_size for f in project_dir.rglob("*") if f.is_file()
                    )
                    projects.append(
                        {
                            "name": project_dir.name,
                            "size_bytes": project_size,
                        }
                    )

        stats["projects"] = projects
        stats["total_size_bytes"] = total_size
        return stats
