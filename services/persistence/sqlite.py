"""
SQLite persistence backend.

Stores user preferences in a local SQLite file. Suitable for single-server
deployments with any number of users a personal bot realistically serves.

Enabled by setting in ``.env``:
    PERSISTENCE_BACKEND=sqlite
    SQLITE_DB_PATH=data/bot.db   # optional; this is the default path

Thread safety
~~~~~~~~~~~~~
``sqlite3`` is used with ``check_same_thread=False``. This is safe here
because:
- SQLite serialises writes internally via file locking.
- Python's GIL prevents true parallel Python execution.
- Writes are rare (only on provider switch) and reads are short (once per user per bot startup).

For a deployment at significant scale, replace this backend with one
backed by PostgreSQL and asyncpg.
"""

import logging
import sqlite3
from pathlib import Path

from services.persistence.base import PersistenceBackend

logger = logging.getLogger(__name__)

# SQL executed once at startup to create the table if it doesn't exist.
# Using INTEGER PRIMARY KEY gives us an implicit rowid alias, which is
# the fastest lookup key in SQLite.
_CREATE_TABLE = """
    CREATE TABLE IF NOT EXISTS user_prefs (
        user_id INTEGER PRIMARY KEY,
        provider TEXT NOT NULL,
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
"""

_UPSERT = """
    INSERT INTO user_prefs (user_id, provider, updated_at)
    VALUES (?, ?, datetime('now'))
    ON CONFLICT(user_id) DO UPDATE SET
        provider = excluded.provider,
        updated_at = excluded.updated_at
"""

_SELECT_PROVIDER = "SELECT provider FROM user_prefs WHERE user_id = ?"


class SQLiteBackend(PersistenceBackend):
    """
    Persistent backend backed by a local SQLite database file.

    Args:
        db_path: Path to the SQLite file. The parent directory is
                 created automatically if it does not exist.
                 Defaults to ``"data/bot.db"``.
    """

    def __init__(self, db_path: str = "data/bot.db") -> None:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute(_CREATE_TABLE)
        self._conn.commit()
        logger.info("SQLiteBackend: database ready at %r", db_path)
    
    def load_provider(self, user_id: int) -> str | None:
        """
        Return the saved provider key for a user.

        Args:
            user_id: Telegram user ID.

        Returns:
            Provider key string, or ``None`` if the user has no saved
            preference (first-time user or MemoryBackend was used before).
        """
        row = self._conn.execute(_SELECT_PROVIDER, (user_id,)).fetchone()
        provider = row[0] if row else None
        logger.debug("SQLiteBackend.load_provider: user=%s -> %r", user_id, provider)
        return provider
    
    def save_provider(self, user_id: int, provider_key: str) -> None:
        """
        Persist the chosen provider key for a user.

        Uses an INSERT … ON CONFLICT … DO UPDATE (upsert) so both new
        users and returning users are handled with a single statement.

        Args:
            user_id:      Telegram user ID.
            provider_key: Provider key to persist (e.g. ``"groq"``).
        """
        self._conn.execute(_UPSERT, (user_id, provider_key))
        self._conn.commit()
        logger.debug("SQLiteBackend.save_provider: user=%s -> %r", user_id, provider_key)
    
    def close(self) -> None:
        """
        Close the database connection cleanly on bot shutdown."""
        self._conn.close()
        logger.info("SQLiteBackend: connection closed.")