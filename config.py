"""
Central configuration module for the Telegram bot.
 
All runtime settings are loaded from environment variables, which are
typically stored in a local `.env` file (never committed to version control).
Every other module in the project should import constants from here instead
of reading environment variables directly.
 
Required variables (must be set before running the bot):
    BOT_TOKEN       — Telegram Bot API token (from @BotFather).
    OPENAI_API_KEY  — OpenAI API key, OR a Groq API key when using Groq.
 
Optional variables (have sensible defaults):
    AI_PROVIDER     — Which AI backend to use: "openai" (default) or "groq".
    AI_MODEL        — Model name override. Defaults depend on the provider.
    AI_BASE_URL     — Custom API base URL. Required when using Groq or any
                      other OpenAI-compatible provider.
    LOG_LEVEL       — Python logging level string, e.g. "INFO" or "DEBUG".
                      Defaults to "INFO".
"""

import os
import logging

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load .env file
# ---------------------------------------------------------------------------
# python-dotenv reads a `.env` file from the project root and injects its
# key=value pairs into the process environment. If the file does not exist
# (e.g. on a server where vars are set at the OS level), this is a no-op.
load_dotenv()


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _require(name: str) -> str:
    """Return the value of environment variable *name*.
 
    Raises:
        EnvironmentError: If the variable is not set or is empty. This
            intentionally crashes at startup rather than failing silently
            later when the variable is first used.
    """

    value = os.getenv(name)
    if not value:
        raise EnvironmentError(
            f"Required environment variable '{name}' is not set. "
            f"Please add it to your .env file or export it in your shell."
            )
    return value


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------
 
#: Telegram Bot API token obtained from @BotFather.
BOT_TOKEN: str = _require("BOT_TOKEN")

# ---------------------------------------------------------------------------
# AI Provider
# ---------------------------------------------------------------------------

#: Which AI provider to use. Supported values are "openai", "groq".
#: Additional providers can be added in services/ai_factory.py later.
AI_PROVIDER: str = os.getenv("AI_PROVIDER", "openai").strip().lower()

#: Raw API key — works for both OpenAI and Groq (they share the same param
#: name in the OpenAI-compatible SDK).
OPENAI_API_KEY: str = _require("OPENAI_API_KEY")

# Default model names per provider. These are used when AI_MODEL is not
# explicitly set in the environment.
_DEFAULT_MODELS: dict[str, str] = {
    "openai": "gpt-4o-mini",
    "groq": "llama3-70b-8192",
}

#: The model that will be used for chat completions.
#: Can be overridden via the AI_MODEL environment variable.
AI_MODEL: str = os.getenv("AI_MODEL", "").strip() or _DEFAULT_MODELS.get(AI_PROVIDER, "gpt-4o-mini")

# Default base URLs per provider. OpenAI's SDK uses its own default when
# base URL is None, so we only need to set this explicitly for other providers.
_DEFAULT_BASE_URLS: dict[str, str] = {
    "openai": None,  # SDK default
    "groq": "https://api.groq.com/v1",
}

#: Base URL for the AI API. Leave unset (or set to "") to use the SDK default
#: (correct for standard OpenAI usage). Must be set for Groq and other
#: OpenAI-compatible providers.
AI_BASE_URL: str | None = os.getenv("AI_BASE_URL", "").strip() or _DEFAULT_BASE_URLS.get(AI_PROVIDER)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

#: Python logging level. Passed to logging.basicConfig in main.py.
LOG_LEVEL: int = os.getenv("LOG_LEVEL", "INFO").strip().upper()


# ---------------------------------------------------------------------------
# Startup validation summary (printed once when the module is first imported)
# ---------------------------------------------------------------------------

def log_config_summary() -> None:
    """Log a human-readable summary of the active configuration.
 
    Call this once from main.py after logging is initialised. It helps
    confirm at a glance that the correct provider, model, and log level
    are active — without printing any sensitive values like API keys.
    """

    logger = logging.getLogger(__name__)
    logger.info("=== Bot configuration ===")
    logger.info("  AI provider : %s", AI_PROVIDER)
    logger.info("  AI model    : %s", AI_MODEL)
    logger.info("  Base URL    : %s", AI_BASE_URL or "(SDK default)")
    logger.info("  Log level   : %s", LOG_LEVEL)
    logger.info("=========================")