"""
Global error handler for the Telegram bot.

Registered in main.py via application.add_error_handler(handle_error).
Catches unhandled exceptions from all command, callback, and message
handlers and sends a user-friendly message instead of crashing silently
or surfacing a raw traceback.
"""

import logging

import openai
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import BadRequest

logger = logging.getLogger(__name__)

async def handle_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Top-level error handler. Called by python-telegram-bot whenever an
    exception propagates out of any registered handler.

    Maps known AI provider errors to short, clear messages.
    All other errors are logged in full and produce a generic reply.
    """
    error = context.error

    if isinstance(error, openai.RateLimitError):
        msg = (
            "⚠️ Провайдер AI тимчасово недоступний — перевищено ліміт запитів.\n\n"
            "Зачекайте кілька хвилин і спробуйте знову, "
            "або оберіть іншого провайдера через /model."
        )
    elif isinstance(error, openai.InternalServerError):
        msg = (
            "⚠️ Сервер AI зараз перевантажений і не відповідає.\n\n"
            "Це тимчасово. Спробуйте ще раз за хвилину "
            "або оберіть іншого провайдера через /model."
        )
    elif isinstance(error, openai.APIConnectionError):
        msg = (
            "⚠️ Не вдалося з'єднатися з AI сервером.\n\n"
            "Перевірте підключення до мережі або спробуйте пізніше."
        )
    elif isinstance(error, openai.AuthenticationError):
        msg = (
            "⚠️ Помилка автентифікації AI провайдера.\n\n"
            "API ключ відсутній або недійсний. "
            "Перевірте налаштування у файлі .env."
        )
    elif isinstance(error, BadRequest) and "can't parse entities" in str(error).lower():
        logger.warning("Telegram entity parse error (malformed AI markdown): %s", error)
        msg = (
            "⚠️ AI повернув текст із некоректним форматуванням, і Telegram не зміг його відобразити.\n\n"
            "Спробуйте ще раз — зазвичай наступна відповідь виходить нормально."
        )
    elif isinstance(error, BadRequest):
        logger.warning("Telegram BadRequest: %s", error)
        msg = (
            "⚠️ Не вдалося надіслати повідомлення — Telegram відхилив запит.\n\n"
            "Спробуйте ще раз або поверніться до меню: /start"
        )
    else:
        logger.error("Unhandled exception in handler:", exc_info=error, stack_info=True)
        msg = (
            "❌ Виникла неочікувана помилка.\n\n"
            "Спробуйте ще раз або поверніться до меню: /start"
        )
    
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(msg)