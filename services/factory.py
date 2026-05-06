"""
Factory function for creating the active AI service.
 
The rest of the application never instantiates a particular service class
directly. Instead it calls ``create_ai_service()``, which picks the first
available provider from the registry and returns the appropriate
``AIService`` implementation.
 
This is only used as a placeholder on first user contact. The real service
is swapped in by ``set_user_provider()`` in ``state.py`` once the user
picks a provider on the model selection screen.

Adding a new provider in the future only requires:
1. Adding a ProviderConfig entry in services/providers.py.
2. Nothing here needs to change.
"""

import logging
import os

from services.base import AIService
from services.openai_service import OpenAIService

logger = logging.getLogger(__name__)

def create_ai_service() -> AIService:
    """
    Create a placeholder AI service for a new user session.

    Uses the first available provider (by key order in providers.py).
    If no provider keys are configured at all, returns a non-functional
    placeholder — it will be replaced by set_user_provider() before the
    user reaches any real AI feature, since model_selection() is always
    shown first.

    Returns:
        A ready-to-use ``AIService`` instance (or an inert placeholder).
    """
    from services.providers import available_providers

    providers = available_providers()

    if not providers:
        logger.warning(
            "No AI provider API keys found in environment. "
            "All providers will appear locked on the model selection screen. "
            "Returning a placeholder service — no AI calls will succeed until "
            "the user picks a provider (which requires a key to be configured)."
        )
        # Return a non-crashing placeholder. It will never be used for real
        # AI calls because model_selection() blocks the user before that.
        return OpenAIService(
            api_key="placeholder",
            model="none",
            base_url=None,
        )

    # Use the first available provider as the initial placeholder.
    # The user will replace this immediately on the model selection screen.
    p = providers[0]
    logger.info(
        "Initialising placeholder AI service with provider %r (model=%r).", 
        p.key, os.getenv("AI_MODEL", "").strip() or p.default_model
    )
    return OpenAIService(
        api_key=os.getenv(p.api_key_env, ""),
        model=os.getenv("AI_MODEL", "").strip() or p.default_model,
        base_url=p.base_url,
    )