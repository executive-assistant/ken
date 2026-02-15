from __future__ import annotations

from pathlib import Path

from src.storage.user_storage import UserStorage


class TestUserStorage:
    def test_create_user_storage(self, temp_data_path: Path) -> None:
        storage = UserStorage(
            user_id="user-123",
            base_path=temp_data_path,
        )
        assert storage.user_id == "user-123"
        assert storage.user_root == temp_data_path / "users" / "user-123"

    def test_ensure_user_dir_creates_directory(self, temp_data_path: Path) -> None:
        storage = UserStorage(
            user_id="new-user",
            base_path=temp_data_path,
        )
        assert not storage.user_root.exists()
        storage.ensure_user_dir()
        assert storage.user_root.exists()
        assert storage.auth_dir.exists()

    def test_auth_dir_path(self, temp_data_path: Path) -> None:
        storage = UserStorage(
            user_id="user-456",
            base_path=temp_data_path,
        )
        assert storage.auth_dir == temp_data_path / "users" / "user-456" / ".auth"

    def test_save_and_load_google_auth(self, temp_user_path: Path) -> None:
        storage = UserStorage(
            user_id="test-user-123",
            base_path=temp_user_path.parent.parent,
        )
        storage.ensure_user_dir()

        tokens = {
            "access_token": "ya29.test-token",
            "refresh_token": "1//test-refresh",
            "expires_at": 1234567890,
        }

        storage.save_google_auth(tokens)
        loaded = storage.load_google_auth()

        assert loaded is not None
        assert loaded["access_token"] == "ya29.test-token"
        assert loaded["refresh_token"] == "1//test-refresh"

    def test_load_google_auth_returns_none_when_missing(self, temp_user_path: Path) -> None:
        storage = UserStorage(
            user_id="test-user-no-auth",
            base_path=temp_user_path.parent.parent,
        )
        storage.ensure_user_dir()
        assert storage.load_google_auth() is None

    def test_save_and_load_microsoft_auth(self, temp_user_path: Path) -> None:
        storage = UserStorage(
            user_id="test-user-ms",
            base_path=temp_user_path.parent.parent,
        )
        storage.ensure_user_dir()

        tokens = {
            "access_token": "eyJ0eXAiOiJKV1QiLCJub25jZSI6I",
            "refresh_token": "0.ARoA6Wg",
            "expires_at": 1234567890,
        }

        storage.save_microsoft_auth(tokens)
        loaded = storage.load_microsoft_auth()

        assert loaded is not None
        assert loaded["access_token"] == "eyJ0eXAiOiJKV1QiLCJub25jZSI6I"

    def test_create_sqlite(self, temp_user_path: Path) -> None:
        storage = UserStorage(
            user_id="test-user-sqlite",
            base_path=temp_user_path.parent.parent,
        )
        storage.ensure_user_dir()

        db_path = storage.create_sqlite("projects/my-project/data.db")
        assert db_path.exists()
        assert db_path.suffix == ".db"

    def test_create_sqlite_creates_parent_dirs(self, temp_user_path: Path) -> None:
        storage = UserStorage(
            user_id="test-user-sqlite-nested",
            base_path=temp_user_path.parent.parent,
        )
        storage.ensure_user_dir()

        db_path = storage.create_sqlite("deeply/nested/path/data.db")
        assert db_path.exists()
        assert db_path.parent.parent.parent.exists()

    def test_create_lancedb(self, temp_user_path: Path) -> None:
        storage = UserStorage(
            user_id="test-user-lance",
            base_path=temp_user_path.parent.parent,
        )
        storage.ensure_user_dir()

        lance_path = storage.create_lancedb("projects/my-project/vectors.lance")
        assert lance_path.exists()
        assert lance_path.is_dir()

    def test_create_lancedb_creates_parent_dirs(self, temp_user_path: Path) -> None:
        storage = UserStorage(
            user_id="test-user-lance-nested",
            base_path=temp_user_path.parent.parent,
        )
        storage.ensure_user_dir()

        lance_path = storage.create_lancedb("deeply/nested/vectors.lance")
        assert lance_path.exists()

    def test_get_project_path(self, temp_user_path: Path) -> None:
        storage = UserStorage(
            user_id="test-user-path",
            base_path=temp_user_path.parent.parent,
        )
        storage.ensure_user_dir()

        project_path = storage.get_project_path("my-project")
        expected = storage.user_root / "projects" / "my-project"
        assert project_path == expected

    def test_get_sqlite_path(self, temp_user_path: Path) -> None:
        storage = UserStorage(
            user_id="test-user-sqlite-path",
            base_path=temp_user_path.parent.parent,
        )
        storage.ensure_user_dir()

        db_path = storage.get_sqlite_path("data/my-data.db")
        expected = storage.user_root / "data" / "my-data.db"
        assert db_path == expected

    def test_get_lancedb_path(self, temp_user_path: Path) -> None:
        storage = UserStorage(
            user_id="test-user-lance-path",
            base_path=temp_user_path.parent.parent,
        )
        storage.ensure_user_dir()

        lance_path = storage.get_lancedb_path("vectors/knowledge.lance")
        expected = storage.user_root / "vectors" / "knowledge.lance"
        assert lance_path == expected

    def test_list_projects_empty(self, temp_user_path: Path) -> None:
        storage = UserStorage(
            user_id="test-user-empty",
            base_path=temp_user_path.parent.parent,
        )
        storage.ensure_user_dir()

        projects = storage.list_projects()
        assert projects == []

    def test_list_projects(self, temp_user_path: Path) -> None:
        storage = UserStorage(
            user_id="test-user-list",
            base_path=temp_user_path.parent.parent,
        )
        storage.ensure_user_dir()

        storage.create_sqlite("projects/project-a/data.db")
        storage.create_sqlite("projects/project-b/data.db")

        projects = storage.list_projects()
        assert len(projects) == 2
        assert "project-a" in projects
        assert "project-b" in projects
