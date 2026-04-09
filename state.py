"""
Per-user dialog state for the Telegram bot.
 
The Problem
~~~~~~~~~~~
The original project stored all session data in a single global ``Dialog``
object and a single global ``ChatGptService`` instance. Because these were
shared across *all* users, any two users interacting with the bot at the
same time would corrupt each other's state — one user's message could be
routed into another user's quiz, and their messages would be mixed into the
same AI conversation history.
 
The Solution
~~~~~~~~~~~~
``python-telegram-bot`` provides ``context.user_data``: a plain dictionary
that the framework automatically keeps separate for each user (keyed by
their Telegram user ID). We store a ``DialogState`` instance and an
``AIService`` instance inside it. Every handler retrieves them via the
``get_user_state()`` helper, which creates them on first access
(lazy initialisation).
 
This means:
- Each user has their own ``mode``, ``quiz_theme``, etc.
- Each user has their own isolated AI conversation history.
- No global variables. No shared mutable state.
 
Usage
~~~~~
In any handler function:
 
    from state import get_user_state
 
    async def some_handler(update, context):
        state, ai = get_user_state(context)
        state.mode = "quiz"
        answer = await ai.add_message("Python")
"""

import logging

from telegram.ext import ContextTypes

from services import AIService, create_ai_service

logger = logging.getLogger(__name__)

# Key used to store the DialogState instance inside context.user_data.
_STATE_KEY = "dialog_state"

# Key used to store the AIService instance inside context.user_data.
_AI_KEY = "ai_service"

class DialogState:
    """
    Holds all session state for a single user's conversation with the bot.
 
    Each attribute tracks one aspect of what the user is currently doing.
    All attributes are instance-level (set in ``__init__``), so two
    ``DialogState`` objects never share any data.
 
    Attributes:
        mode:        The current active feature. Controls how incoming
                     text messages are routed in ``handlers/messages.py``.
                     See ``Modes`` below for valid values.
        quiz_theme:  The selected quiz topic. Only meaningful when
                     ``mode`` is ``"quiz"`` or ``"quiz_started"``.
        translation: Tracks whether a target language has been chosen in
                     the translator feature. ``"started"`` means a language
                     is active and incoming text should be translated.
        category:    The selected recommendations category (movies / books /
                     music). Only meaningful when ``mode`` is
                     ``"recommendations_started"``.
 
    Modes (valid values for ``self.mode``)::
 
        "default"                 — No active feature; show main menu.
        "gpt"                     — Free-form GPT chat.
        "dialog_started"          — Talking to a historical figure.
        "quiz"                    — Quiz topic selection screen.
        "quiz_started"            — Quiz in progress; answers expected.
        "voice_chat_gpt"          — Voice message mode.
        "translator"              — Language selection screen.
        "recommendations"         — Category selection screen.
        "recommendations_started" — Recommendations in progress.
        "image_recognition"       — Waiting for an image or URL.
        "cv"                      — CV generator; collecting user info.
        "random"                  — Random facts mode.
    """

    def __init__(self) -> None:
        self.mode: str = "default"
        self.quiz_theme: str = "none"
        self.translation: str = "not_started"
        self.category: str = "none"

    def reset(self) -> None:
        """
        Reset all state to defaults.
 
        Call this when the user returns to the main menu so that stale
        state from a previous session cannot affect the next one.
        """
        self.mode: str = "default"
        self.quiz_theme: str = "none"
        self.translation: str = "not_started"
        self.category: str = "none"
        logger.debug("DialogState reset to defaults")
    
    def __repr__(self) -> str:
        return (f"DialogState(mode={self.mode!r}, quiz_theme={self.quiz_theme!r}, "
                f"translation={self.translation!r}, category={self.category!r})"
        )


def get_user_state(context: ContextTypes.DEFAULT_TYPE,) -> tuple[DialogState, AIService]:
    """
    Return the ``DialogState`` and ``AIService`` for the current user.
 
    Both objects are stored inside ``context.user_data`` and created on
    first access (lazy initialisation). On every subsequent call for the
    same user, the existing objects are returned — preserving conversation
    history and dialog state across messages.
 
    Args:
        context: The handler context provided by python-telegram-bot.
                 ``context.user_data`` is keyed by Telegram user ID and is
                 automatically isolated per user by the framework.
 
    Returns:
        A ``(DialogState, AIService)`` tuple for the current user.
 
    Example:
 
        async def my_handler(update, context):
            state, ai = get_user_state(context)
            state.mode = "gpt"
            response = await ai.add_message(update.message.text)
    """

    # Lazily create DialogState for this user on first message.
    if _STATE_KEY not in context.user_data:
        context.user_data[_STATE_KEY] = DialogState()
        logger.debug("Created new DialogState for user %s", context._user_id)
    
    # Lazily create a dedicated AIService instance for this user.
    # Each user gets their own instance so their message history is
    # completely isolated from every other user's.
    if _AI_KEY not in context.user_data:
        context.user_data[_AI_KEY] = create_ai_service()
        logger.debug("Created new AIService for user %s", context._user_id)
    
    return context.user_data[_STATE_KEY], context.user_data[_AI_KEY]