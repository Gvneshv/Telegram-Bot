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
    "quiz_prog": lambda u, c: _set_quiz_theme_and_ask(u, c, "quiz_prog"),
    "quiz_math": lambda u, c: _set_quiz_theme_and_ask(u, c, "quiz_math"),
    "quiz_biology": lambda u, c: _set_quiz_theme_and_ask(u, c, "quiz_biology"),
    "quiz_more": _quiz_more,
    "quiz_change_theme": _quiz_change_theme,
    "quiz_end_btn": start,

    # --- Talk (persona selection) ---
    "talk_1": lambda u, c: start_persona(u, c, "talk_1"),
    "talk_2": lambda u, c: start_persona(u, c, "talk_2"),
    "talk_3": lambda u, c: start_persona(u, c, "talk_3"),
    "talk_4": lambda u, c: start_persona(u, c, "talk_4"),
    "talk_5": lambda u, c: start_persona(u, c, "talk_5"),
    "talk_end_btn": start,

    # --- Translator ---
    "translate_english": lambda u, c: select_language(u, c, "translate_english"),
    "translate_german": lambda u, c: select_language(u, c, "translate_german"),
    "translate_italian": lambda u, c: select_language(u, c, "translate_italian"),
    "translate_french": lambda u, c: select_language(u, c, "translate_french"),
    "translate_spanish": lambda u, c: select_language(u, c, "translate_spanish"),    
    "translate_change": translator,
    "translate_end_btn": start,

    # --- Recommendations ---
    "recommendations_movies": lambda u, c: select_category(u, c, "movies"),
    "recommendations_books": lambda u, c: select_category(u, c, "books"),
    "recommendations_music": lambda u, c: select_category(u, c, "music"),
    "recommendations_dislike": lambda u, c: select_category(u, c, feedback="dislike"),
    "recommendations_end_btn": _recommendations_end,

    # --- CV ---
    "cv_start_over": _cv_start_over,
    "cv_end_btn": start,
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

    if handler is None:
        logger.warning("Unhandled callback_data: %r", query)
        await send_text(update, context, "Невідома дія. Будь ласка, скористайтесь меню /start.")
        return
    
    await handler(update, context)