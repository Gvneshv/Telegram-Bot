"""
Helper functions for sending messages, images, and menus via the Telegram
Bot API.
 
All functions in this module are thin wrappers around ``context.bot`` and
``update`` calls. Keeping them here rather than scattered across handler
files means:
 
- The Telegram API call details live in one place.
- Handler functions stay focused on *what* to send, not *how* to send it.
- If the API changes or we want to add retry logic, we change it here once.
 
Every function is ``async`` because all Telegram Bot API calls are I/O
operations and must be awaited.
"""

import logging
from telegram import (
    BotCommand,
    BotCommandScopeChat,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    MenuButtonCommands,
    MenuButtonDefault,
    Update,
)

from telegram.constants import ParseMode
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

async def send_text(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        text: str,
) -> Message:
    """
    Send a plain Markdown message to the current chat.
 
    Uses ``ParseMode.MARKDOWN``. If the text contains an odd number of
    underscores (which would break Markdown parsing), the function logs a
    warning and falls back to sending the message as plain HTML to avoid
    a Telegram API error crashing the bot.
 
    Args:
        update:  The incoming Telegram update.
        context: The handler context provided by python-telegram-bot.
        text:    The message text, optionally containing Markdown formatting.
 
    Returns:
        The ``Message`` object returned by the Telegram API.
    """
    # Odd number of underscores breaks Markdown — fall back to HTML.
    if text.count('_') % 2 != 0:
        logger.warning(
            "send_text: text contains an odd number of underscores, "
            "which is invalid Markdown. Falling back to send_html."
        )
        return await send_html(update, context, text)
    
    # Re-encode through UTF-16 to handle surrogate characters that can
    # appear in some Unicode text (e.g. certain emoji sequences).
    safe_text = text.encode('utf-16', errors='surrogatepass').decode('utf-16')

    return await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=safe_text,
        parse_mode=ParseMode.MARKDOWN,
    )

async def send_html(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        text: str,
) -> Message:
    """
    Send an HTML-formatted message to the current chat.
 
    Use this instead of ``send_text`` when the message content may contain
    Markdown-incompatible characters, or when you need HTML tags like
    ``<b>``, ``<i>``, or ``<code>``.
 
    Args:
        update:  The incoming Telegram update.
        context: The handler context provided by python-telegram-bot.
        text:    The message text with optional HTML formatting.
 
    Returns:
        The ``Message`` object returned by the Telegram API.
    """
    # Re-encode through UTF-16 to handle surrogate characters that can
    # appear in some Unicode text (e.g. certain emoji sequences).
    safe_text = text.encode('utf-16', errors='surrogatepass').decode('utf-16')

    return await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=safe_text,
        parse_mode=ParseMode.HTML,
    )

async def send_text_buttons(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        text: str,
        buttons: dict[str, str],
) -> Message:
    """
    Send a message with an inline keyboard attached.
 
    Each entry in ``buttons`` becomes one keyboard row with a single button.
    The dict key is used as the ``callback_data`` value (what the bot
    receives when the button is pressed); the dict value is the visible
    button label.
 
    Args:
        update:  The incoming Telegram update.
        context: The handler context provided by python-telegram-bot.
        text:    The message text shown above the keyboard.
        buttons: Ordered mapping of ``{callback_data: button_label}``.
 
    Returns:
        The ``Message`` object returned by the Telegram API.
 
    Example:
 
        await send_text_buttons(update, context, "Choose an option:", {
            "opt_yes": "✅ Yes",
            "opt_no":  "❌ No",
        })
    """
    safe_text = text.encode('utf-16', errors='surrogatepass').decode('utf-16')
    
    # Build one row per button so they stack vertically, which is the
    # clearest layout for menus with more than two options.
    keyboard = [
        [InlineKeyboardButton(label, callback_data=key)]
        for label, key in buttons.items()
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    return await context.bot.send_message(
        chat_id=update.effective_message.chat_id,
        text=safe_text,
        reply_markup=reply_markup,
        message_thread_id=update.effective_message.message_thread_id,
)

async def send_image(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        name: str,
) -> Message:
    """
    Send an image from the ``resources/images/`` directory.
 
    Looks for a JPEG file at ``resources/images/<name>.jpg`` and sends it
    to the current chat.
 
    Args:
        update:  The incoming Telegram update.
        context: The handler context provided by python-telegram-bot.
        name:    The image filename without path or extension
                 (e.g. ``"main"`` → ``resources/images/main.jpg``).
 
    Returns:
        The ``Message`` object returned by the Telegram API.
 
    Raises:
        FileNotFoundError: If the image file does not exist.
    """
    image_path = f"resources/images/{name}.jpg"

    with open(image_path, 'rb') as image_file:
        return await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=image_file,
        )

async def show_main_menu(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        commands: dict[str, str],
) -> None:
    """
    Register bot commands and show the menu button for the current chat.
 
    Sets the list of slash commands visible in the Telegram command menu
    (the ``/`` button in the message input bar) scoped to the current chat.
    Also enables the menu button so the list is accessible.
 
    Args:
        update:   The incoming Telegram update.
        context:  The handler context provided by python-telegram-bot.
        commands: Ordered mapping of ``{command_name: description}``.
                  Command names should not include the leading slash.
 
    Example::
 
        await show_main_menu(update, context, {
            "start": "Main menu",
            "gpt":   "Chat with GPT 🤖",
        })
    """
    command_list = [BotCommand(key, value) for key, value in commands.items()]

    await context.bot.set_my_commands(
        command_list,
        scope=BotCommandScopeChat(chat_id=update.effective_chat.id),
    )
    await context.bot.set_chat_menu_button(
        chat_id=update.effective_chat.id,
        menu_button=MenuButtonCommands(),
    )

async def hide_main_menu(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Remove bot commands and hide the menu button for the current chat.
 
    Reverses the effect of ``show_main_menu``. Useful when the bot enters
    a mode where commands should be hidden (e.g. mid-conversation).
 
    Args:
        update:  The incoming Telegram update.
        context: The handler context provided by python-telegram-bot.
    """
    await context.bot.delete_my_commands(
        scope=BotCommandScopeChat(chat_id=update.effective_chat.id),
    )
    await context.bot.set_chat_menu_button(
        chat_id=update.effective_chat.id,
        menu_button=MenuButtonDefault(),
    )