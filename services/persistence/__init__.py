"""
Persistence package - pluggable storage backend for user preferences.

The active backend is a module-level singleton initialised once at startup
by ``main.py`` via ``init_backend()``. All other modules call
``get_backend()`` to retrieve it; they never construct a backend directly.

Available backends
------------------
MemoryBackend  - no-op, identical to pre-persistence behaviour (default).
SQLiteBackend  - lightweight single-file storage, zero infrastructure.

To switch backend, set ``PERSISTENCE_BACKEND`` in ``.env``:
    PERSISTENCE_BACKEND=none    # default - no persistence
    PERSISTENCE_BACKEND=sqlite  # SQLite file at SQLITE_DB_PATH
"""

from services.persistence.base import PersistenceBackend
from services.persistence.memory import MemoryBackend

# Module-level singleton. Set once by main.py, read by state.py.
# Default to MemoryBackend so the bot works correctly even if
# init_backend() is never called (e.g. in tests).
_backend: PersistenceBackend = MemoryBackend()


def init_backend(backend: PersistenceBackend) -> None:
    """
    Register the active persistence backend.

    Must be called exactly once at bot startup, before any handler runs.

    Args:
        backend: The backend instance to activate.
    """
    global _backend
    _backend = backend


def get_backend() -> PersistenceBackend:
    """
    Return the currently active persistence backend.

    Returns:
        The backend registered via ``init_backend()``, or a
        ``MemoryBackend`` if ``init_backend()`` was never called.
    """
    return _backend