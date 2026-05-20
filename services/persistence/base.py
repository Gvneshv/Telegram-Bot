"""
Abstract interface for persistence backends.

Any new backend (Postgres, Redis, …) implements this interface.
The rest of the codebase only depends on this abstraction - it never
imports a concrete backend class directly.
"""

from abc import ABC, abstractmethod


class PersistenceBackend(ABC):
    @abstractmethod
    def get_user_prompt(self, user_id: int) -> str:
        """
        Minimal key-value interface for persisting per-user preferences.

        Only the fields worth storing across sessions are represented here.
        Ephemeral session data (mode, quiz theme, etc.) stays in memory.
        """
        
        @abstractmethod
        def load_provider(self, user_id: int) -> str | None:
            """
            Return the saved provider key for a user, or None if not found.

            Args:
                user_id: Telegram user ID.

            Returns:
                A provider key string (e.g. ``"groq"``), or ``None``.
            """

        @abstractmethod
        def save_provider(self, user_id: int, provider_key: str) -> None:
            """
            Persist the chosen provider key for a user.

            Overwrites any previously saved value. Must be durable - the
            value should survive a full bot restart.

            Args:
                user_id:      Telegram user ID.
                provider_key: The provider key to store (e.g. ``"groq"``).
            """

        @abstractmethod
        def close(self) -> None:
            """
            Release any resources held by the backend (connections, file handles).

            Called once on bot shutdown. Implementations that hold no resources may leave this as a no-op.
            """