"""
Handler for all inline keyboard button presses (``CallbackQueryHandler``).
 
Design
~~~~~~
The original project registered five separate callback handler functions,
each with its own ``pattern=`` regex and its own ``if/elif`` chain. This
scattered routing logic across both the handler functions and the
registration site in ``main.py``.
 
Here, a single ``handle_callback`` function is registered for *all* button
presses (no pattern filter). Inside it, a flat ``_ROUTES`` dispatch table
maps every ``callback_data`` string directly to the coroutine that should
run. This means:
 
- Routing logic lives in exactly one place.
- Adding a new button requires one new entry in ``_ROUTES``.
- The ``main.py`` registration is a single line.
 
The ``_ROUTES`` table is built at module load time from small, clearly
labelled sections — one per feature — so it remains easy to navigate even
as the button count grows.
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from handlers.commands import (
    cv,
    quiz,
    recommendations,
    select_category,
    select_language,
    send_quiz_question,
    start,
    start_persona,
    translator
)

from state import get_user_state
from utils.messaging import send_text

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Route table
# ---------------------------------------------------------------------------
# Maps every callback_data string to an async callable with the signature:
#   async (update, context) -> None
#
# Entries are grouped by feature for readability. The table is built once
# at import time and never modified at runtime.
# ---------------------------------------------------------------------------

async def _quiz_more(u: Update, c: ContextTypes.DEFAULT_TYPE) -> None:
    """Request another question on the current quiz topic."""
    # quiz_theme is already set from the previous topic selection —
    # we just ask for another question without changing it.
    await send_quiz_question(u, c)


async def _quiz_change_theme(u: Update, c: ContextTypes.DEFAULT_TYPE) -> None:
    """Return to the quiz topic selection screen."""
    state, _ = get_user_state(c)
    state.quiz_theme = "none"
    await quiz(u, c)


async def _recommendations_end(u: Update, c: ContextTypes.DEFAULT_TYPE) -> None:
    """End the recommendations session and return to the main menu."""
    state, _ = get_user_state(c)
    state.mode = "default"
    state.category = "none"
    await start(u, c)


async def _cv_start_over(u: Update, c: ContextTypes.DEFAULT_TYPE) -> None:
    """Restart the CV generator from scratch."""
    await cv(u, c)


# The main routing table. Keys are callback_data strings exactly as set
# in the InlineKeyboardButton definitions in handlers/commands.py.
_ROUTES: dict[str, object] = {
    # Note: "more_btn" and "end_btn" (random facts feature) are handled as
    # special cases directly in handle_callback below to avoid a circular
    # import between this module and handlers/commands.py.

    # --- Quiz ---
    "Програмування": lambda u, c: _set_quiz_theme_and_ask(u, c, "quiz_prog"),
    "Математика": lambda u, c: _set_quiz_theme_and_ask(u, c, "quiz_math"),
    "Біологія": lambda u, c: _set_quiz_theme_and_ask(u, c, "quiz_biology"),
    "Більше питань": _quiz_more,
    "Змінити тему": _quiz_change_theme,
    "Закінчити": start,

    # --- Talk (persona selection) ---
    "Курт Кобейн": lambda u, c: start_persona(u, c, "talk_1"),
    "Колишня Королева Об'єднаного Королівства": lambda u, c: start_persona(u, c, "talk_2"),
    "Джон Толкін": lambda u, c: start_persona(u, c, "talk_3"),
    "Нітцше": lambda u, c: start_persona(u, c, "talk_4"),
    "Стівен Гокінг": lambda u, c: start_persona(u, c, "talk_5"),
    "Закінчити": start,

    # --- Translator ---
    "Англійська 🇬🇧": lambda u, c: select_language(u, c, "Англійська 🇬🇧"),
    "Німецька 🇩🇪": lambda u, c: select_language(u, c, "translate_german"),
    "Італійська 🇮🇹": lambda u, c: select_language(u, c, "translate_italian"),
    "Французька 🇫🇷": lambda u, c: select_language(u, c, "translate_french"),
    "Іспанська 🇪🇸": lambda u, c: select_language(u, c, "translate_spanish"),    
    "Змінити мову": translator,
    "Закінчити переклад": start,

    # --- Recommendations ---
    "Рекомендації фільмів": lambda u, c: select_category(u, c, "movies"),
    "Рекомендації книг": lambda u, c: select_category(u, c, "books"),
    "Рекомендації музики": lambda u, c: select_category(u, c, "music"),
    "Не подобається": lambda u, c: select_category(u, c, feedback="dislike"),
    "Закінчити": _recommendations_end,

    # --- CV ---
    "Почати спочатку": _cv_start_over,
    "Закінчити": start,
}


# ---------------------------------------------------------------------------
# Quiz theme helper (needs state access, so defined after _ROUTES)
# ---------------------------------------------------------------------------

async def _set_quiz_theme_and_ask(update: Update, context: ContextTypes.DEFAULT_TYPE, theme: str) -> None:
    """
    Set the quiz theme on the user's state and ask the first question.
 
    Args:
        update:  The incoming Telegram update.
        context: The handler context.
        theme:   One of the quiz topic keys (e.g. ``"quiz_prog"``).
    """
    state, _ = get_user_state(context)
    state.mode = "quiz_started"
    state.quiz_theme = theme
    await send_quiz_question(update, context)


# ---------------------------------------------------------------------------
# Main dispatcher
# ---------------------------------------------------------------------------

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Dispatch all inline keyboard button presses to the correct handler.
 
    This is the single ``CallbackQueryHandler`` registered in ``main.py``.
    It answers the callback query (removes the loading indicator from the
    button), looks up the pressed button's ``callback_data`` in ``_ROUTES``,
    and calls the associated handler.
 
    If the ``callback_data`` is not found in ``_ROUTES``, a warning is
    logged and the user receives a short error message. This prevents
    silent failures if a stale message with old buttons is pressed after
    a bot update.
 
    Args:
        update:  The incoming Telegram update containing the callback query.
        context: The handler context provided by python-telegram-bot.
    """
    # Always answer the callback query first. This removes the loading
    # spinner from the button and prevents "query timeout" errors in
    # the Telegram client if the handler takes a moment to complete.
    await update.callback_query.answer()

    query = update.callback_query.data
    logger.debug(f"Received callback query: {query!r} from user {update.effective_user.id}")

    # --- Special cases that need a local import to avoid circular imports ---
    # "more_btn" and "end_btn" come from the /random feature. Importing
    # `random` at the top of this file would create a circular dependency
    # (commands → callbacks → commands), so we import it here instead.
    if query == "more_btn":
        from handlers.commands import random as random_fact
        await random_fact(update, context)
        return
    
    if query == "end_btn":
        await start(update, context)
        return
    
    # --- Standard routing via the _ROUTES table ---
    handler = _ROUTES.get(query)

    if handler is not None:
        logger.warning("Unhandled callback_data: %r", query)
        await send_text(update, context, "Невідома дія. Будь ласка, скористайтесь меню /start.")
        return
    
    await handler(update, context)