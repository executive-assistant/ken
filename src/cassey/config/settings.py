"""Application settings with environment variable loading."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM Configuration
    DEFAULT_LLM_PROVIDER: Literal["anthropic", "openai", "zhipu"] = "anthropic"
    ANTHROPIC_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None
    ZHIPUAI_API_KEY: str | None = None

    # Telegram Configuration
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_WEBHOOK_URL: str | None = None
    TELEGRAM_WEBHOOK_SECRET: str | None = None

    # Storage Configuration
    CHECKPOINT_STORAGE: Literal["postgres", "memory"] = "postgres"
    POSTGRES_URL: str = "postgresql://cassey:cassey_password@localhost:5432/cassey_db"

    # Security / File Sandbox
    FILES_ROOT: Path = Field(default=Path("./files"))
    MAX_FILE_SIZE_MB: int = 10

    # DuckDB Storage
    DUCKDB_ROOT: Path = Field(default=Path("./duckdb"))

    # Context Management
    MAX_CONTEXT_TOKENS: int = 100_000  # Max tokens before summarization
    ENABLE_SUMMARIZATION: bool = True  # Enable running summaries by default
    SUMMARY_THRESHOLD: int = 20  # Summarize after N messages

    # Allowed file extensions for file operations
    ALLOWED_FILE_EXTENSIONS: set[str] = Field(
        default={
            ".txt",
            ".md",
            ".py",
            ".js",
            ".ts",
            ".json",
            ".yaml",
            ".yml",
            ".csv",
            ".xml",
            ".html",
            ".css",
            ".sh",
            ".bash",
        }
    )

    @field_validator("FILES_ROOT", mode="before")
    @classmethod
    def resolve_files_root(cls, v: str | Path) -> Path:
        """Resolve files root to absolute path."""
        return Path(v).resolve()

    @field_validator("DUCKDB_ROOT", mode="before")
    @classmethod
    def resolve_duckdb_root(cls, v: str | Path) -> Path:
        """Resolve DuckDB root to absolute path."""
        return Path(v).resolve()

    def get_files_path(self, user_id: str) -> Path:
        """Get files path for a specific user."""
        user_path = self.FILES_ROOT / user_id
        user_path.mkdir(parents=True, exist_ok=True)
        return user_path


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Singleton instance
settings = get_settings()
