"""
Factory function for creating the active AI service.
 
The rest of the application never instantiates a particular service class
directly. Instead it calls ``create_ai_service()``, which reads the
provider settings from ``config.py`` and returns the appropriate
``AIService`` implementation.
 
Adding a new provider in the future only requires:
1. Writing a new class that inherits from ``AIService`` (in its own module).
2. Adding a branch in ``create_ai_service()`` below.
Nothing else in the codebase needs to change.
"""

import logging

import config
from services.base import AIService
from services.openai_service import OpenAIService

logger = logging.getLogger(__name__)

def create_ai_service() -> AIService:
    """
    Instantiate and return the AI service specified in ``config.py``.
 
    Reads ``config.AI_PROVIDER``, ``config.OPENAI_API_KEY``,
    ``config.AI_MODEL``, and ``config.AI_BASE_URL`` to build the service.
 
    Returns:
        A ready-to-use ``AIService`` instance.
 
    Raises:
        ValueError: If ``config.AI_PROVIDER`` names an unsupported provider.
 
    Example:
 
        # In main.py
        from services.factory import create_ai_service
        ai = create_ai_service()
    """
    provider = config.AI_PROVIDER
    logger.info("Creating AI service for provider: %s", provider)

    if provider in ("openai", "groq"):
        # Both OpenAI and Groq use the same SDK-compatible client.
        # The difference is purely in base_url and model, both of which
        # config.py resolves automatically based on AI_PROVIDER.
        return OpenAIService(
            api_key=config.OPENAI_API_KEY,
            model=config.AI_MODEL,
            base_url=config.AI_BASE_URL,
        )
    
    # ----------------------------------------------------------------
    # Future providers — add branches here:
    #
    # elif provider == "gemini":
    #     from services.gemini_service import GeminiService
    #     return GeminiService(api_key=config.OPENAI_API_KEY, model=config.AI_MODEL)
    #
    # elif provider == "ollama":
    #     from services.ollama_service import OllamaService
    #     return OllamaService(model=config.AI_MODEL, base_url=config.AI_BASE_URL)
    # ----------------------------------------------------------------

    raise ValueError(
        f"Unsupported AI provider: '{provider}'. "
        f"Set AI_PROVIDER in your .env to one of: openai, groq."
    )