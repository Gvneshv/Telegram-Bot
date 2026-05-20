"""
In-memory (no-op) persistence backend.

Stores nothing. Behaviour is identical to the bot before persistence
was introduced. This is the default backend when
``PERSISTENCE_BACKEND`` is not set or is set to ``"none"``.
"""

from services.persistence.base import PersistenceBackend


class MemoryBackend(PersistenceBackend):
    """
    No-op backend — all methods are intentional no-ops.
    """

    def load_provider(self, user_id: int) -> str | None:
        """
        Always returns None — nothing is ever stored.
        """
        return None
    
    def save_provider(self, user_id: int, provider_key: str) -> None:
        """
        Discards the value — nothing is ever written.
        """
    
    def close(self) -> None:
        """
        Nothing to release.
        """