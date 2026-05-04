"""
Command handler functions for every slash command the bot supports.
 
Each function here is registered in ``main.py`` with a ``CommandHandler``
and is called by the framework when the corresponding ``/command`` is sent.
 
All handlers follow the same pattern:
1. Retrieve the per-user ``(state, ai)`` pair via ``get_user_state()``.
2. Update ``state.mode`` to reflect the active feature.
3. Set the AI system prompt if the feature needs one.
4. Send the appropriate image and text to the user.
 
Persona data (for the "talk" feature) and dispatch tables (for quiz topics
and translation languages) are defined as module-level constants so they
can be extended without modifying any function bodies.
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from state import get_user_state
from utils.messaging import send_html, send_image, send_text, send_text_buttons, show_main_menu
from utils.resources import load_message, load_prompt

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# "Talk" personas
# ---------------------------------------------------------------------------
# Each entry defines a historical figure the user can converse with.
# Keys are the callback_data strings used by the inline keyboard buttons
# (defined in the ``talk`` command below).
#
# To add a new persona:
#   1. Add an entry here.
#   2. Add a button for it in the ``talk()`` function's button dict.
#   3. Add a prompt file at resources/prompts/talk_<key>.txt
#   4. Add an image at resources/images/talk_<key>.jpg
#
# No other code needs to change.

PERSONAS: dict[str, dict[str, str]] = {
    "talk_1": {
        "image": "talk_cobain",
        "prompt": "talk_cobain",
        "greeting": "Привіт. Кобейн говорить. Шо там по питаннях?",
    },
    "talk_2": {
        "image": "talk_queen",
        "prompt": "talk_queen",
        "greeting": "Наливайте 'Ерл Ґрей', до вас говорить Королева.",
    },
    "talk_3": {
        "image": "talk_tolkien",
        "prompt": "talk_tolkien",
        "greeting": "Вітання із Середзем'я. Тут Толкін, що бажаєш обговорити?",
    },
    "talk_4": {
        "image": "talk_nietzsche",
        "prompt": "talk_nietzsche",
        "greeting": "Guten Tag. Ніцше на зв'язку. Які питання вас турбують?",
    },
    "talk_5": {
        "image": "talk_hawking",
        "prompt": "talk_hawking",
        "greeting": "Привіт, це Стівен Вільям Гокінг. Про що хочеш поговорити?",
    },
}


# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /start command — show the main menu.
 
    Resets all user state so there is no carry-over from a previous
    feature session. Sends the main image, the welcome message, registers
    all available slash commands in the Telegram menu, and shows an inline
    keyboard so users can launch any feature with a single tap.
 
    This function is also called programmatically by other handlers
    (e.g. when the user presses an "End" button) to return to the menu.
    """
    state, ai = get_user_state(context)
    state.reset()   # Clear any stale state from a previous session.
    ai.set_prompt("You are a helpful Telegram bot assistant.")

    text = load_message("main")
    await send_image(update, context, "main")

    await show_main_menu(update, context, {
        "start":             "Головне меню 🏠",
        # "random":            "Випадковий цікавий факт 🧠",
        # "gpt":               "Запитати ChatGPT 🤖",
        # "talk":              "Поговорити з відомою особистістю 👤",
        # "quiz":              "Взяти участь у квізі ❓",
        # "translator":        "Перекласти текст 🌐",
        # "voice_chat_gpt":    "Голосовий ChatGPT 🎙",
        # "recommendations":   "Рекомендації фільмів, книг і музики 🎬",
        # "image_recognition": "Розпізнавання зображень 🖼",
        # "cv":                "Згенерувати резюме 📄",
    })

    # Inline quick-launch menu — 2-column grid, grouped by similarity.
    # Buttons are paired intentionally: text features left, media right;
    # voice + image together since both are provider-limited on Groq.
    await send_text_buttons(update, context, text, {
        "menu_gpt":             "🤖 GPT чат",
        "menu_random":          "🎲 Цікавий факт",
        "menu_talk":            "🗣 Розмова",
        "menu_quiz":            "❓ Квіз",
        "menu_translator":      "🌐 Перекладач",
        "menu_recommendations": "🎬 Рекомендації",
        "menu_voice":           "🎙 Голосовий чат",
        "menu_image":           "🖼 Розпізнавання",
        "menu_cv":              "📄 Резюме",
    }, columns=2)


# ---------------------------------------------------------------------------
# /random
# ---------------------------------------------------------------------------

async def random(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /random — send a random interesting fact via the AI.
 
    Sets ``state.mode`` to ``"random"`` so the "More" inline button
    (handled in ``handlers/callbacks.py``) can call this function again
    for a new fact.
 
    Each call uses ``ai.send_question()`` rather than ``ai.add_message()``
    because facts are stateless — there is no need to maintain history
    between individual fact requests.
    """
    state, ai = get_user_state(context)
    state.mode = "random"

    prompt = load_prompt("random")
    await send_image(update, context, "random")

    # send_question resets history and sends a one-shot prompt + question.
    content = await ai.send_question(prompt, "Дай цікавий факт.")

    await send_text_buttons(update, context, content, {
        "more_btn": "Хочу ще факт 🔄",
        "end_btn":  "Закінчити ✖️",
    })


# ---------------------------------------------------------------------------
# /gpt
# ---------------------------------------------------------------------------

async def gpt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /gpt — start a free-form ChatGPT conversation.
 
    Sets the AI system prompt and ``state.mode`` to ``"gpt"``.
    Subsequent text messages are routed to ``handle_text_message()``
    in ``handlers/messages.py`` for as long as this mode is active.
    """
    state, ai = get_user_state(context)
    state.mode = "gpt"
    
    prompt = load_prompt("gpt")
    ai.set_prompt(prompt)

    text = load_message("gpt")
    await send_image(update, context, "gpt")
    await send_html(update, context, text)


# ---------------------------------------------------------------------------
# /talk  +  persona helper
# ---------------------------------------------------------------------------

async def talk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /talk — show the persona selection menu.
 
    Sets ``state.mode`` to ``"talk"`` so the callback handler in
    ``handlers/callbacks.py`` knows which button presses to respond to.
    The actual persona setup happens in ``start_persona()`` once the user
    picks a character.
    """
    state, ai = get_user_state(context)
    state.mode = "talk"

    text = load_message("talk")
    await send_image(update, context, "talk")
    
    await send_text_buttons(update, context, text, {
        "talk_1":    "Курт Кобейн — соліст 'Nirvana' 🎸",
        "talk_2":    "Єлизавета II — Колишня Королева Об'єднаного Королівства 👑",
        "talk_3":    "Джон Толкін — автор 'Володаря Перснів' 📖",
        "talk_4":    "Фрідріх Ніцше — філософ 🧠",
        "talk_5":    "Стівен Гокінг — астрофізик 🔭",
        "talk_end_btn": "Закінчити ✖️",
    })


async def start_persona(update: Update, context: ContextTypes.DEFAULT_TYPE, persona_key: str) -> None:
    """
    Set up a conversation with a specific historical persona.
 
    Called from ``handlers/callbacks.py`` when the user selects a persona
    button. Loads the persona's image, prompt, and greeting from the
    ``PERSONAS`` constant defined at the top of this module.
 
    Sets ``state.mode`` to ``"dialog_started"`` so subsequent text messages
    are routed to the general ``handle_text_message()`` handler, which
    forwards them to the AI (now configured with the persona's prompt).
 
    Args:
        update:      The incoming Telegram update.
        context:     The handler context.
        persona_key: One of the keys in ``PERSONAS``
                     (e.g. ``"talk_1"`` for Kurt Cobain).
    """
    state, ai = get_user_state(context)
    
    persona = PERSONAS.get(persona_key)
    if persona is None:
        logger.warning("start_persona called with unknown key: %s", persona_key)
        await send_text(update, context, "Невідома особистість. Спробуйте ще раз.")
        return
    
    state.mode = "dialog_started"

    prompt = load_prompt(persona["prompt"])
    ai.set_prompt(prompt)

    await send_image(update, context, persona["image"])
    await send_text(update, context, persona["greeting"])


# ---------------------------------------------------------------------------
# /quiz
# ---------------------------------------------------------------------------

# Maps each quiz topic button's callback_data to the short keyword sent to
# the AI to request a question on that topic.
# To add a new topic: add an entry here and a button in quiz() below.
_QUIZ_TOPIC_PROMPTS: dict[str, str] = {
    "quiz_prog": "Python",
    "quiz_math": "Math",
    "quiz_biology": "Biology",
}


async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /quiz — show the quiz topic selection menu.
 
    Sets the AI system prompt for the quiz feature and ``state.mode``
    to ``"quiz"``. The callback handler in ``handlers/callbacks.py``
    picks up button presses from here.
    """
    state, ai = get_user_state(context)
    state.mode = "quiz"

    prompt = load_prompt("quiz")
    ai.set_prompt(prompt)

    text = load_message("quiz")
    await send_image(update, context, "quiz")
    
    await send_text_buttons(update, context, text, {
        "quiz_prog":    "Програмування мовою Python 🐍",
        "quiz_math":    "Математика (теорії алгоритмів, множин, матаналіз) ➗",
        "quiz_biology": "Біологія 🧬",
        "quiz_end_btn": "Закінчити ✖️",
    })


async def send_quiz_question(update: Update, context: ContextTypes.DEFAULT_TYPE,) -> None:
    """
    Ask the AI for a quiz question based on the current topic.
 
    Reads ``state.quiz_theme`` to determine which topic keyword to send.
    Uses a dispatch table (``_QUIZ_TOPIC_PROMPTS``) instead of if/elif
    branches so the topic list can be extended by editing only the dict.
 
    Called from ``handlers/callbacks.py`` when the user selects a topic
    or requests another question on the same topic.
    """
    state, ai = get_user_state(context)
    
    # "quiz_more" means "same topic again" — reuse the current theme.
    topic_key = state.quiz_theme

    # Determine the keyword to send to the AI.
    keyword = _QUIZ_TOPIC_PROMPTS.get(topic_key)

    if keyword is None:
        logger.warning("send_quiz_question: unknown quiz_theme %r", topic_key)
        await send_text(update, context, "Невідома тема. Оберіть тему ще раз.")
        return
    
    await send_image(update, context, "quiz")
    answer = await ai.add_message(keyword)
    await send_text(update, context, answer)


# ---------------------------------------------------------------------------
# /translator
# ---------------------------------------------------------------------------
 
# Maps each language button's callback_data to the keyword sent to the AI
# to switch translation target. The AI's system prompt (resources/prompts/
# translator.txt) is expected to understand these keywords.
# To add a language: add one entry here and one button in translator() below.
_LANGUAGE_KEYWORDS: dict[str, str] = {
    "translate_english": "english",
    "translate_german":  "german",
    "translate_italian": "italian",
    "translate_french":  "french",
    "translate_spanish": "spanish",
}

async def translator(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /translator — show the language selection menu.
 
    Loads the translator system prompt and sets ``state.mode`` to
    ``"translator"``. The selected language is handled in
    ``handlers/callbacks.py``.
    """
    state, ai = get_user_state(context)
    state.mode = "translator"
    state.translation = "not_started"

    prompt = load_prompt("translator")
    ai.set_prompt(prompt)

    text = load_message("translator")
    await send_image(update, context, "translator")
    
    await send_text_buttons(update, context, text, {
        "translate_english": "Англійська 🇬🇧",
        "translate_german":  "Німецька 🇩🇪",
        "translate_italian": "Італійська 🇮🇹",
        "translate_french":  "Французька 🇫🇷",
        "translate_spanish": "Іспанська 🇪🇸",
        "translate_end_btn":     "Закінчити ✖️",
    })


async def select_language(update: Update, context: ContextTypes.DEFAULT_TYPE, callback_key: str) -> None:
    """
    Confirm a translation language and begin waiting for input.
 
    Called from ``handlers/callbacks.py`` when the user presses a language
    button. Informs the AI of the chosen language and sets
    ``state.translation`` to ``"started"`` so incoming text messages are
    routed to the translation handler.
 
    Args:
        update:       The incoming Telegram update.
        context:      The handler context.
        callback_key: The callback_data of the pressed button
                      (e.g. ``"translate_english"``).
    """
    state, ai = get_user_state(context)
    
    keyword = _LANGUAGE_KEYWORDS.get(callback_key)
    if keyword is None:
        logger.warning("select_language: unknown callback_key %r", callback_key)
        return

    state.translation = "started"
    # Reset mode back to "translator" so the message handler routes
    # subsequent text to handle_translator_message().
    state.mode = "translator"

    # Tell the AI which language to use. The reply is discarded — it is an
    # internal acknowledgment of the language setting, not user-facing content.
    await ai.add_message(keyword)

    # Show the user a clean prompt in with action buttons.
    await send_image(update, context, "translator")
    await send_text_buttons(update, context, "Що бажаєте перекласти?", {
        "translate_change": "Змінити мову 🌐",
        "translate_end_btn":    "Закінчити ✖️",
    })


# ---------------------------------------------------------------------------
# /voice_chat_gpt
# ---------------------------------------------------------------------------

async def voice_chat_gpt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /voice_chat_gpt — enable voice message mode.
 
    Sets ``state.mode`` to ``"voice_chat_gpt"``. While this mode is active,
    incoming voice messages are processed by ``handle_voice()`` in
    ``handlers/messages.py`` and replied to with a synthesised voice answer.
 
    Note:
        Voice features (Whisper STT + TTS) require an OpenAI API key.
        They are not available when using the Groq provider.
    """
    state, ai = get_user_state(context)
    state.mode = "voice_chat_gpt"

    text = load_message("voice_chat_gpt")
    await send_image(update, context, "voice_chat_gpt")
    await send_text(update, context, text)


# ---------------------------------------------------------------------------
# /recommendations
# ---------------------------------------------------------------------------

# Maps state.category to the "already seen/read/listened" button label.
_SEEN_LABELS: dict[str, str] = {
    "movies": "Вже дивився 👀",
    "books":  "Вже читав 📖",
    "music":  "Вже слухав 🎧",
}

async def recommendations(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /recommendations — show the category selection menu.
 
    Loads the recommendations system prompt and sets ``state.mode``
    to ``"recommendations"``. Category selection and subsequent
    conversation are handled in ``handlers/callbacks.py`` and
    ``handlers/messages.py``.
    """
    state, ai = get_user_state(context)
    state.mode = "recommendations"

    prompt = load_prompt("recommendations")
    ai.set_prompt(prompt)

    text = load_message("recommendations")
    await send_image(update, context, "recommendations")
    
    await send_text_buttons(update, context, text, {
        "recommendations_movies": "Фільми 🎬",
        "recommendations_books":  "Книги 📚",
        "recommendations_music":  "Музика 🎵",
        "recommendations_end_btn": "Закінчити ✖️",
    })


async def select_category(update: Update, context: ContextTypes.DEFAULT_TYPE, category: str) -> None:
    """
    Request recommendations for the given category from the AI.
 
    Called from ``handlers/callbacks.py`` when the user selects a category
    button (movies / books / music) or presses "Dislike" to get different
    suggestions in the same category.
 
    Uses a dispatch table to map category keys to Ukrainian keywords that
    are sent to the AI, replacing the original series of if/elif branches.
 
    Args:
        update:   The incoming Telegram update.
        context:  The handler context.
        category: One of ``"movies"``, ``"books"``, ``"music"``,
                  or ``"dislike"``.
    """
    state, ai = get_user_state(context)
    state.mode = "recommendations_started"

    # Only update state.category for real category picks, not for feedback actions.
    if category not in ("dislike", "seen"):
        state.category = category

    # Maps the category key to the message sent to the AI.
    # "dislike" asks for different recommendations in the same category.
    _category_messages: dict[str, str] = {
        "movies":  "Фільми",
        "books":   "Книги",
        "music":   "Музика",
        "dislike": "Не подобається. Надішли інше у тій же категорії та жанрі",
        "seen":    "Вже бачив/читав/слухав і сподобалось. Порекомендуй щось схоже",
    }

    message = _category_messages.get(category)
    if message is None:
        logger.warning("select_category: unknown category %r", category)
        return

    answer = await ai.add_message(message)

    seen_label = _SEEN_LABELS.get(state.category, "Вже бачив 👀")
    
    await send_text_buttons(update, context, answer, {
        "recommendations_seen": seen_label,
        "recommendations_dislike": "Не подобається 👎",
        "recommendations_change": "Змінити категорію 🔀",
        "recommendations_end_btn": "Закінчити ✖️",
    })


# ---------------------------------------------------------------------------
# /image_recognition
# ---------------------------------------------------------------------------

async def image_recognition(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /image_recognition — enable image analysis mode.
 
    Sets the AI vision prompt and ``state.mode`` to ``"image_recognition"``.
    While this mode is active, incoming photos are handled by
    ``handle_image_recognition_message()`` in ``handlers/messages.py``.
 
    Note:
        Vision features require a model that supports image input
        (e.g. ``gpt-4o-mini``). LLaMA-based Groq models do not support
        image analysis.
    """
    state, ai = get_user_state(context)
    state.mode = "image_recognition"

    prompt = load_prompt("image_recognition")
    ai.set_prompt(prompt)

    text = load_message("image_recognition")
    await send_image(update, context, "image_recognition")
    await send_text(update, context, text)


# ---------------------------------------------------------------------------
# /cv
# ---------------------------------------------------------------------------

async def cv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /cv — start the CV (curriculum vitae) generator.
 
    Loads the CV system prompt and sets ``state.mode`` to ``"cv"``.
    The user is expected to send information about themselves in subsequent
    messages, which are handled by ``handle_cv_message()`` in
    ``handlers/messages.py``.
    """
    state, ai = get_user_state(context)
    state.mode = "cv"

    prompt = load_prompt("cv")
    ai.set_prompt(prompt)

    text = load_message("cv")
    await send_image(update, context, "cv")
    await send_text(update, context, text)