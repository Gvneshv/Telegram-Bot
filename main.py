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
import html
import json
import logging
import traceback

import config
from telegram import Update
from telegram.constants import ParseMode
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
    random,
    recommendations,
    start,
    talk,
    translator,
    voice_chat_gpt,
)
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
# Error handler
# ---------------------------------------------------------------------------

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Log unhandled exceptions and notify the chat where the error occurred.
 
    python-telegram-bot calls this for any exception that propagates out of
    a handler function. It logs the full traceback at ERROR level and sends
    a formatted HTML message to the chat so the user knows something went
    wrong.
 
    The message includes the full traceback and the raw update, which is
    useful during development. For a production deployment you may want to
    send the detailed report only to a dedicated admin chat and show the
    user a simpler "something went wrong" message.
 
    Args:
        update:  The update that caused the error (may not be a
                 ``telegram.Update`` instance in some edge cases).
        context: The handler context; ``context.error`` holds the exception.
    """
    logger = logging.getLogger(__name__)
    logger.error("Unhandled exception in handler:", exc_info=context.error)

    # Build the traceback string.
    tb_lines = traceback.format_exception(
        None, 
        context.error, 
        context.error.__traceback__
    )
    tb_string = "".join(tb_lines)

    # Serialise the update for display.
    update_str = (
        update.to_dict() if isinstance(update, Update) else str(update)
    )

    message = (
        "<b>An exception was raised while handling an update.</b>\n\n"
        f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}</pre>\n\n"
        f"<pre>chat_data  = {html.escape(str(context.chat_data))}</pre>\n"
        f"<pre>user_data  = {html.escape(str(context.user_data))}</pre>\n\n"
        f"<pre>{html.escape(tb_string)}</pre>"
    )

    # Send to the chat where the error occurred, if can determine it.
    if isinstance(update, Update) and update.effective_chat:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
            parse_mode=ParseMode.HTML,
        )


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
    app.add_error_handler(error_handler)


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