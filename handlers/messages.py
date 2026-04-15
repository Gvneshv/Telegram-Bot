"""
Message handler functions for text, voice, and photo inputs.
 
There are two categories of handler here:
 
1. **Feature-specific handlers** — ``handle_text_message``,
   ``handle_quiz_message``, ``handle_translator_message``,
   ``handle_rec_message``, ``handle_cv_message``.
   Each handles text input for one specific feature.
 
2. **Media handlers** — ``handle_voice`` and ``handle_image_message``.
   These deal with non-text message types regardless of the current mode.
 
3. **The router** — ``handle_message``.
   A single ``MessageHandler(filters.TEXT, ...)`` is registered in
   ``main.py``. All text messages flow through ``handle_message``, which
   reads ``state.mode`` and delegates to the correct feature handler.
 
Bug fixes from the original
~~~~~~~~~~~~~~~~~~~~~~~~~~~
- The router used ``if`` instead of ``elif``, meaning multiple branches
  could fire for a single message if state changed mid-function. All
  branches are now ``elif`` so exactly one handler runs per message.
- Voice and image files were saved to hardcoded filenames (``user_voice.mp3``,
  ``answer.mp3``, ``image.jpg``). Two users sending media simultaneously
  would overwrite each other's files. Files are now named with the chat ID
  (e.g. ``voice_123456.mp3``) so each user's files are independent.
- ``handle_voice`` had a bare ``except AttributeError`` that silently
  swallowed errors and could leave ``path`` undefined. Error handling is
  now explicit and logs the full context.
"""

import logging
import os

from telegram import Update
from telegram.ext import ContextTypes

from state import get_user_state
from utils.messaging import send_text, send_text_buttons

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Feature-specific text handlers
# ---------------------------------------------------------------------------

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Forward a plain text message to the AI and reply with the response.
 
    Used by: free-form GPT chat (``mode == "gpt"``) and the historical
    persona dialogues (``mode == "dialog_started"``).
 
    The AI's conversation history is maintained automatically across calls
    because ``ai.add_message()`` appends to the per-user message list.
 
    Args:
        update:  The incoming Telegram update.
        context: The handler context provided by python-telegram-bot.
    """
    _, ai = get_user_state(context)
    text = update.message.text
    answer = await ai.get_response(text)
    await send_text(update, context, answer)


async def handle_quiz_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle a user's answer during an active quiz session.
 
    Sends the user's answer to the AI and returns the AI's evaluation
    along with buttons to continue or change topic.
 
    Used by: ``mode == "quiz_started"``.
 
    Args:
        update:  The incoming Telegram update.
        context: The handler context provided by python-telegram-bot.
    """
    _, ai = get_user_state(context)
    text = update.message.text
    answer = await ai.add_message(text)
    
    await send_text_buttons(update, context, answer, {
        "quiz_more":         "Інше питання на ту ж тему 🔄",
        "quiz_change_theme": "Змінити тему 📚",
        "quiz_end_btn":      "Закінчити ✖️",
    })


async def handle_translator_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Translate the user's text into the currently selected language.
 
    Used by: ``mode == "translator"`` with ``state.translation == "started"``.
    The AI has already been primed with the target language via
    ``select_language()`` in ``handlers/commands.py``.
 
    Args:
        update:  The incoming Telegram update.
        context: The handler context provided by python-telegram-bot.
    """
    _, ai = get_user_state(context)
    text = update.message.text
    answer = await ai.get_response(text)
    
    await send_text_buttons(update, context, answer, {
        "translate_change": "Змінити мову 🌐",
        "translate_end":    "Закінчити ✖️",
    })


async def handle_rec_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle a genre or preference input during a recommendations session.
 
    The user typically sends a genre (e.g. "sci-fi") or a mood, and the AI
    responds with tailored recommendations.
 
    Used by: ``mode == "recommendations_started"``.
 
    Args:
        update:  The incoming Telegram update.
        context: The handler context provided by python-telegram-bot.
    """
    _, ai = get_user_state(context)
    text = update.message.text
    answer = await ai.get_response(text)
    
    await send_text_buttons(update, context, answer, {
        "recommendations_dislike": "Не подобається 👎",
        "recommendations_end_btn": "Закінчити ✖️",
    })


async def handle_cv_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle a block of personal/professional information for CV generation.
 
    The user sends information about themselves (experience, skills, etc.)
    and the AI returns a formatted CV section. The conversation continues
    until the user is satisfied or presses "Start over".
 
    Used by: ``mode == "cv"``.
 
    Args:
        update:  The incoming Telegram update.
        context: The handler context provided by python-telegram-bot.
    """
    _, ai = get_user_state(context)
    text = update.message.text
    answer = await ai.add_message(text)
    
    await send_text_buttons(update, context, answer, {
        "cv_start_over": "Почати спочатку 🔄",
        "cv_end_btn":    "На головну 🏠",
    })


# ---------------------------------------------------------------------------
# Media handlers
# ---------------------------------------------------------------------------

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Process a voice message and reply with a synthesised voice answer.
 
    Workflow:
        1. Download the voice file from Telegram.
        2. Transcribe it to text using Whisper (STT).
        3. Send the transcript to the AI and get a text response.
        4. Synthesise the response as audio using TTS.
        5. Send the audio file back to the user.
        6. Clean up temporary files.
 
    File naming: temporary files use the chat ID in their name
    (e.g. ``voice_123456789.mp3``) so that concurrent voice messages
    from different users do not overwrite each other's files.
 
    Note:
        STT (Whisper) and TTS require an OpenAI API key. They are not
        available when using the Groq provider. If called with Groq active,
        the user will receive an error message.
 
    Args:
        update:  The incoming Telegram update containing the voice message.
        context: The handler context provided by python-telegram-bot.
    """
    _, ai = get_user_state(context)

    chat_id = update.effective_chat.id

    # Use chat_id-scoped filenames to prevent collisions between users.
    voice_input_path  = f"voice_{chat_id}_input.mp3"
    voice_output_path = f"voice_{chat_id}_output.mp3"

    try:
        # Step 1: Download the voice file from Telegram.
        file_id = update.message.voice.file_id
        bot = update.get_bot()
        file = await bot.get_file(file_id)
        await file.download_to_drive(voice_input_path)
        logger.debug(f"Downloaded voice message from user {chat_id} to {voice_input_path}")

        # Step 2: Transcribe to text using Whisper (STT).
        transcript = await ai.speech_to_text(voice_input_path)
        logger.debug(f"Transcribed voice message from user {chat_id}: {transcript!r}")

        # Step 3: Send the transcript to the AI and get a text response.
        await ai.add_message(transcript)  # Add the user's message to the conversation history.
        text_answer = await ai.add_message(transcript)

        # Step 4: Synthesise the response as audio using TTS.
        await ai.text_to_speech(text_answer, voice_output_path)

        # Step 5: Send the audio file back to the user.
        with open(voice_output_path, "rb") as audio:
            await bot.send_voice(chat_id=chat_id, voice=audio)
    
    except AttributeError:
        # update.message.voice is None — the handler was triggered by a
        # non-voice message somehow. Log and ignore.
        logger.warning(
            "handle_voice called but update.message.voice is None "
            "(chat_id=%s). Ignoring.", chat_id
        )
    
    except NotImplementedError:
        # The active AI provider does not support voice features. Inform the user.
        await send_text(
            update, context, 
            "Голосові функції доступні лише з провайдером OpenAI. "
            "Змінити провайдера можна в налаштуваннях бота (AI_PROVIDER у .env).")
    
    except Exception:
        logger.exception("Unexpected error in handle_voice (chat_id=%s)", chat_id)
        await send_text(
            update, context, 
            "Сталася помилка при обробці голосового повідомлення. "
            "Будь ласка, спробуйте ще раз.")
    
    finally:
        # Step 6: Clean up temporary files regardless of success or failure.
        for path in (voice_input_path, voice_output_path):
            if os.path.exists(path):
                os.remove(path)
                logger.debug(f"Deleted temporary file {path} for user {chat_id}")


async def handle_image_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Analyse a photo sent by the user and describe its contents.
 
    Downloads the highest-resolution version of the photo, passes it to
    the AI's vision model, and sends the description back.
 
    File naming: uses the chat ID so that concurrent image messages from
    different users do not overwrite each other's files.
 
    Note:
        Vision requires a model that supports image input (e.g.
        ``gpt-4o-mini``). LLaMA-based Groq models do not currently support
        image analysis — the user will receive an error message if Groq is
        the active provider.
 
    Args:
        update:  The incoming Telegram update containing the photo.
        context: The handler context provided by python-telegram-bot.
    """
    _, ai = get_user_state(context)

    chat_id = update.effective_chat.id
    image_path = f"image_{chat_id}.jpg"

    try:
        # ``update.message.photo`` is a list of PhotoSize objects in
        # ascending resolution. ``[-1]`` is always the highest quality.
        file_id = update.message.photo[-1].file_id
        bot = update.get_bot()
        file = await bot.get_file(file_id)
        await file.download_to_drive(image_path)
        logger.debug(f"Downloaded image from user {chat_id} to {image_path}")

        answer = await ai.recognize_image(image_path)
        await send_text(update, context, answer)
    
    except NotImplementedError:
        # The active AI provider does not support vision features. Inform the user.
        await send_text(
            update, context, 
            "Аналіз зображень доступний лише з провайдером OpenAI."
            "(моделі з підтримкою зображень, наприклад gpt-4o-mini)."
            "Змінити провайдера можна в налаштуваннях бота (AI_PROVIDER у .env)."
        )
    
    except Exception:
        logger.exception("Unexpected error in handle_image_message (chat_id=%s)", chat_id)
        await send_text(
            update, context, 
            "Сталася помилка при обробці зображення. "
            "Будь ласка, спробуйте ще раз.")
    
    finally:
        if os.path.exists(image_path):
            os.remove(image_path)
            logger.debug(f"Deleted temporary file {image_path} for user {chat_id}")


# ---------------------------------------------------------------------------
# Message router
# ---------------------------------------------------------------------------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Route incoming text messages to the correct feature handler.
 
    This is the single ``MessageHandler(filters.TEXT, ...)`` entry point
    registered in ``main.py``. It reads ``state.mode`` (and
    ``state.translation`` for the translator) and delegates to the
    appropriate handler.
 
    Important: all branches use ``elif`` (not ``if``) so that exactly one
    handler runs per message, even if a handler somehow modifies state
    mid-function. Using plain ``if`` chains (as in the original code)
    risks multiple handlers firing for a single message.
 
    Unrecognised modes are logged as a warning. The user receives no
    response in that case, which is the correct behaviour when no feature
    is active (e.g. the user sends a random message before typing /start).
 
    Args:
        update:  The incoming Telegram update.
        context: The handler context provided by python-telegram-bot.
    """
    state, _ = get_user_state(context)
    mode = state.mode

    logger.debug(
        "handle_message: mode=%r, translation=%r",
        mode, state.translation,
    )

    if mode == "gpt":
        await handle_text_message(update, context)
    
    elif mode == "dialog_started":
        await handle_text_message(update, context)
    
    elif mode == "quiz_started":
        await handle_quiz_message(update, context)
    
    elif state.translation == "started" and mode == "translator":
        # Translation mode: active whenever a language has been chosen.
        await handle_translator_message(update, context)
    
    elif mode == "voice_chat_gpt":
        # Text sent while in voice mode is treated as a regular GPT message,
        # giving the user a text response. Voice messages are handled
        # separately by handle_voice() via MessageHandler(filters.VOICE).
        await handle_text_message(update, context)
    
    elif mode == "recommendations_started":
        await handle_rec_message(update, context)

    elif mode == "image_recognition":
        # In image recognition mode, text messages are treated as URL inputs
        # or follow-up questions — forward them to the AI as plain text.
        await handle_text_message(update, context)

    elif mode == "cv":
        await handle_cv_message(update, context)
    
    else:
        # No active feature — the user sent a message outside of any session.
        # Log it but don't respond, to avoid spamming the user when they
        # send something before pressing /start.
        logger.debug(
            "Received text message with no active mode (chat_id=%s, text=%r). No handler for mode=%r Ignoring.",
            update.effective_chat.id, update.message.text, mode,
        )