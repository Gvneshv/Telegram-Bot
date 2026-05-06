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
    gpt,
    image_recognition,
    model_selection,
    quiz,
    random as random_command,
    recommendations,
    select_category,
    select_language,
    send_quiz_question,
    start,
    start_persona,
    talk,
    translator,
    voice_chat_gpt,
)

from services.providers import PROVIDERS, available_providers, get_provider
from state import get_user_state, set_user_provider
from utils.messaging import send_text

logger = logging.getLogger(__name__)

# Built once at import time. Contains callback_data strings for providers
# that have no API key — used in handle_callback to fire show_alert popups.
_UNAVAILABLE_PROVIDER_CALLBACKS: frozenset[str] = frozenset(
    p.callback_data for p in PROVIDERS if p not in available_providers()
)


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


async def _select_provider(update: Update, context: ContextTypes.DEFAULT_TYPE, provider_key: str) -> None:
    """Activate the chosen provider and proceed to the feature menu."""
    provider = get_provider(provider_key)
    if provider is None:
        logger.error("Unknown provider key: %s", provider_key)
        return
    
    set_user_provider(context, provider)

    # Show which features are limited with this provider.
    warnings = []
    if not provider.supports_voice:
        warnings.append("🎙 Голосовий чат — недоступний")
    if not provider.supports_vision:
        warnings.append("🖼 Розпізнавання зображень — недоступне")
    
    if warnings:
        note = "⚠️ З цією моделлю деякі функції обмежені:\n" + "\n".join(warnings)
        await send_text(update, context, note)
    
    # Hand off to the regular feature menu.
    await start(update, context)


# The main routing table. Keys are callback_data strings exactly as set
# in the InlineKeyboardButton definitions in handlers/commands.py.
_ROUTES: dict[str, object] = {
    # Note: "more_btn" and "end_btn" (random facts feature) are handled as
    # special cases directly in handle_callback below to avoid a circular
    # import between this module and handlers/commands.py.

    # --- Model selection ---
    "model_groq":   lambda u, c: _select_provider(u, c, "groq"),
    "model_openai": lambda u, c: _select_provider(u, c, "openai"),
    # "model_gemini": lambda u, c: _select_provider(u, c, "gemini")

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
    "recommendations_seen": lambda u, c: select_category(u, c, "seen"),
    "recommendations_dislike": lambda u, c: select_category(u, c, "dislike"),
    "recommendations_change": recommendations,
    "recommendations_end_btn": _recommendations_end,

    # --- CV ---
    "cv_start_over": _cv_start_over,
    "cv_end_btn": start,

    # --- Main menu (quick-launch buttons on /start) ---
    "menu_gpt":             gpt,
    "menu_random":          random_command,
    "menu_talk":            talk,
    "menu_quiz":            quiz,
    "menu_translator":      translator,
    "menu_recommendations": recommendations,
    "menu_cv":              cv,
    "menu_voice":           voice_chat_gpt,
    "menu_image":           image_recognition,

    # --- Random fact ---
    "more_btn": random_command,
    "end_btn":  start,
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
    query = update.callback_query.data

    # --- Locked provider buttons: answer with an alert popup, then stop. ---
    # This must happen before the general answer() below so we can pass
    # show_alert=True with a custom message instead of a blank acknowledgement.
    if query in _UNAVAILABLE_PROVIDER_CALLBACKS:
        provider = get_provider(query.replace("model_", ""))
        note = provider.unavailable_note if provider else "Цей провайдер недоступний."
        await update.callback_query.answer(text=note, show_alert=True)
        return
    
    # --- Locked feature buttons (depends on active provider capabilities) ---
    if query in ("menu_voice", "menu_image"):
        state, _ = get_user_state(context)
        provider = get_provider(state.provider) if state.provider else None
        if query == "menu_voice" and provider and not provider.supports_voice:
            await update.callback_query.answer(
                text=(
                    "🎙 Голосовий чат недоступний для цієї моделі.\n\n"
                    "Оберіть ШІ модель з доступом до голосових функцій через /model."
                ), 
                show_alert=True
            )
            return
        
        if query == "menu_image" and provider and not provider.supports_vision:
            await update.callback_query.answer(
                text=(
                    "🖼 Розпізнавання зображень недоступне для цієї моделі.\n\n"
                    "Оберіть ШІ модель з доступом до розпізнавання зображень через /model."
                ), 
                show_alert=True
            )
            return


    # Always answer the callback query first. This removes the loading
    # spinner from the button and prevents "query timeout" errors in
    # the Telegram client if the handler takes a moment to complete.
    await update.callback_query.answer()

    logger.debug(f"Received callback query: {query!r} from user {update.effective_user.id}")
    
    # --- Standard routing via the _ROUTES table ---
    handler = _ROUTES.get(query)

    if handler is None:
        logger.warning("Unhandled callback_data: %r", query)
        await send_text(update, context, "Невідома дія. Будь ласка, скористайтесь меню /start.")
        return
    
    await handler(update, context)