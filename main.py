"""
Entry point for the Telegram bot.
 
Responsibilities:
    1. Initialise logging.
    2. Log the active configuration summary.
    3. Build the ``Application`` instance with the bot token.
    4. Register all command, message, and callback handlers.
    5. Start polling for updates.
 
This module contains no business logic. All handler functions live in the
``handlers/`` package. Configuration is read from ``config.py``.
 
Usage:
 
    python main.py
 
Or via Docker:
 
    docker compose up
"""

import asyncio
import logging
import traceback

import config
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from handlers.callbacks import handle_callback
from handlers.commands import (
    cv,
    gpt,
    image_recognition,
    quiz,
    model_selection,
    random,
    recommendations,
    start,
    talk,
    translator,
    voice_chat_gpt,
)
from handlers.errors import handle_error
from handlers.messages import handle_image_message, handle_message, handle_voice


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def _configure_logging() -> None:
    """
    Set up application-wide logging from ``config.LOG_LEVEL``.
 
    - The root logger is set to the configured level (default: INFO).
    - ``httpx`` is set to WARNING to suppress the noisy per-request logs
      that the Telegram polling loop generates.
    - Log records include timestamp, logger name, level, and message.
    """
    logging.basicConfig(
        format="%(asctime)s | %(name)-24s | %(levelname)-8s | %(message)s",
        level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    )
    # Suppress per-request GET/POST logs from the HTTP client.
    logging.getLogger("httpx").setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# Handler registration
# ---------------------------------------------------------------------------

def _register_handlers(app) -> None:
    """
    Register all command, message, and callback handlers on ``app``.
 
    Kept as a separate function so the registration list is easy to scan
    and extend without wading through startup boilerplate.
 
    Handler priority note: python-telegram-bot runs handlers in the order
    they are registered. ``CommandHandler`` entries must come before the
    catch-all ``MessageHandler(filters.TEXT, ...)`` so that slash commands
    are not accidentally treated as plain text messages.
 
    Args:
        app: The ``Application`` instance built in ``main()``.
    """
    # --- Command handlers (slash commands) ---
    app.add_handler(CommandHandler("start",             start))
    app.add_handler(CommandHandler("random",            random))
    app.add_handler(CommandHandler("gpt",               gpt))
    app.add_handler(CommandHandler("talk",              talk))
    app.add_handler(CommandHandler("quiz",              quiz))
    app.add_handler(CommandHandler("translator",        translator))
    app.add_handler(CommandHandler("voice_chat_gpt",    voice_chat_gpt))
    app.add_handler(CommandHandler("recommendations",   recommendations))
    app.add_handler(CommandHandler("image_recognition", image_recognition))
    app.add_handler(CommandHandler("cv",                cv))
    app.add_handler(CommandHandler("model",             model_selection))

    # --- Message handlers ---
    # VOICE and PHOTO are registered before TEXT so they take priority
    # when a user sends media while in a text-expecting mode.
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO, handle_image_message))
    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    # --- Callback query handler ---
    # A single handler for ALL inline keyboard button presses.
    # Routing to the correct feature is done inside handle_callback via
    # the _ROUTES dispatch table in handlers/callbacks.py.
    app.add_handler(CallbackQueryHandler(handle_callback))

    # --- Error handler ---
    app.add_error_handler(handle_error)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """
    Configure and start the bot.
 
    Builds the ``Application``, registers handlers, and begins long-polling
    for Telegram updates. Blocks until interrupted (Ctrl-C or SIGTERM).

    Note on Python 3.14 compatibility:
        In Python 3.14, ``asyncio.get_event_loop()`` no longer creates a new
        event loop automatically if none exists — it raises ``RuntimeError``
        instead. ``python-telegram-bot``'s ``run_polling()`` calls this
        internally, so we must explicitly create and register an event loop
        before calling it. This is safe and correct on all Python versions.
    """
    _configure_logging()

    logger = logging.getLogger(__name__)
    config.log_config_summary()
    logger.info("Starting bot...")

    # Python 3.14 compatibility: explicitly create an event loop before
    # run_polling() is called, since asyncio.get_event_loop() no longer
    # creates one automatically.
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    app = ApplicationBuilder().token(config.BOT_TOKEN).build()
    _register_handlers(app)

    logging.info("Bot is running, polling for updates... Press Ctrl-C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()