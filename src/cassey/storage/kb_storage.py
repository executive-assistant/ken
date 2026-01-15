"""Knowledge base storage using per-thread DuckDB files."""

from pathlib import Path

from cassey.config import settings
from cassey.storage.db_storage import DBStorage


class KBStorage(DBStorage):
    """KB storage that mirrors DBStorage layout with a separate root."""

    def __init__(self, root: Path | None = None) -> None:
        super().__init__(root or settings.KB_ROOT)


_kb_storage = KBStorage()


def get_kb_storage() -> KBStorage:
    """Get the global KB storage instance."""
    return _kb_storage
