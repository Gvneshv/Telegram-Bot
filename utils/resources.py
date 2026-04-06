"""
Functions for loading static text resources from the ``resources/``
directory.
 
The bot uses two types of text resource files:
 
- **Messages** (``resources/messages/*.txt``) — the text that is sent to
  the user when they enter a feature, e.g. the welcome text for the quiz
  screen.
 
- **Prompts** (``resources/prompts/*.txt``) — the system-level instructions
  sent to the AI to configure its behaviour for a particular feature, e.g.
  "You are Kurt Cobain, answer only in character."
 
Keeping these in plain ``.txt`` files rather than hardcoding them in Python
makes them easy to edit without touching any code, and keeps the handler
logic free of long string literals.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Base directory for all resource files.
# ``Path(__file__)`` resolves to this file's location, so ``parents[1]``
# walks up one level to the project root regardless of where the bot is
# launched from.
_BASE_DIR = Path(__file__).parents[1] / "resources"

def load_message(name: str) -> str:
    """
    Load a user-facing message from ``resources/messages/<name>.txt``.
 
    These files contain the text displayed to the user when they start a
    particular bot feature (e.g. the introductory text for the quiz,
    translator, CV generator, etc.).
 
    Args:
        name: The filename without extension
              (e.g. ``"quiz"`` → ``resources/messages/quiz.txt``).
 
    Returns:
        The file contents as a UTF-8 string with no modifications.
 
    Raises:
        FileNotFoundError: If the file does not exist. This is intentionally
            not caught here — a missing resource file is a deployment error
            that should surface loudly.
 
    Example::
 
        text = load_message("main")
        await send_html(update, context, text)
    """
    path = _BASE_DIR / "messages" / f"{name}.txt"
    logger.debug(f"Loading message: %s", path)
    return path.read_text(encoding="utf-8")

def load_prompt(name: str) -> str:
    """
    Load an AI system prompt from ``resources/prompts/<name>.txt``.
 
    These files contain the system-level instructions passed to the AI
    to configure its persona or behaviour for a specific feature
    (e.g. the "talk to Tolkien" prompt, or the CV generator prompt).
 
    Args:
        name: The filename without extension
              (e.g. ``"talk_cobain"`` → ``resources/prompts/talk_cobain.txt``).
 
    Returns:
        The file contents as a UTF-8 string with no modifications.
 
    Raises:
        FileNotFoundError: If the file does not exist.
 
    Example::
 
        prompt = load_prompt("talk_cobain")
        ai_service.set_prompt(prompt)
    """
    path = _BASE_DIR / "prompts" / f"{name}.txt"
    logger.debug(f"Loading prompt: %s", path)
    return path.read_text(encoding="utf-8")