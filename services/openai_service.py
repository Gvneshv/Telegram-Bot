"""
Particular AI service implementation using the OpenAI Python SDK.
 
Because Groq's API is fully OpenAI-compatible, this same class works for
both providers — you simply point it at a different ``base_url`` and use a
different model name. Both are controlled via ``config.py``, so no code
changes are needed when switching providers.
 
Key improvements over the original ``gpt.py``:
- Blocking SDK calls are wrapped in ``asyncio.to_thread`` so they run in a
  thread pool and never freeze the bot's async event loop.
- ``client`` is no longer passed as a parameter to instance methods — they
  use ``self._client`` directly.
- All conversation state is held in instance attributes (not class-level),
  so each ``OpenAIService`` instance is fully independent.
- Voice output is written to a caller-supplied path instead of a hardcoded
  filename, preventing file collisions when multiple users send voice
  messages at the same time.
"""

import asyncio
import base64
import logging
from pathlib import Path

import httpx
from openai import OpenAI

from services.base import AIService

logger = logging.getLogger(__name__)


class OpenAIService(AIService):
    """AI service backed by the OpenAI API (or any OpenAI-compatible API).
 
    This class is safe to instantiate once per user session (or even once
    globally, since conversation state is stored per-instance). For
    multi-user bots the recommended pattern is to store one instance inside
    ``context.user_data`` so each user has their own isolated history —
    see ``state.py`` for how that is done.
 
    Args:
        api_key:  The provider API key (OpenAI ``sk-...`` or Groq key).
        model:    Chat completion model name, e.g. ``"gpt-4o-mini"`` or
                  ``"llama3-70b-8192"``.
        base_url: Optional base URL override for OpenAI-compatible providers
                  (e.g. ``"https://api.groq.com/openai/v1"`` for Groq).
                  Pass ``None`` to use the OpenAI default.
    """

    def __init__(self, api_key: str, model: str, base_url: str | None = None) -> None:
        self._model = model
        self._message_list: list[dict] = []

        # httpx.Client is passed explicitly so we have full control over
        # connection settings (timeouts, proxies, etc.) in one place.
        self._client = OpenAI(
            api_key=api_key,
            base_url=base_url,  # None → SDK uses api.openai.com
            http_client=httpx.Client(),
        )

        logger.debug(
            "OpenAI service initialized (model=%r, base_url=%r)",
            model,
            base_url or "(default)",
        )
    
    async def _complete(self) -> str:
        """Send the current message list to the API and return the reply.
 
        Runs the blocking SDK call inside a thread pool via
        ``asyncio.to_thread`` so the event loop is never blocked.
        The assistant reply is appended to ``_message_list`` to maintain
        conversation continuity.
 
        Returns:
            The assistant's response as a plain string.
        """
        
        def _blocking_call() -> str:
            completion = self._client.chat.completions.create(
                model=self._model,
                messages=self._message_list,
                max_tokens=3000,
                temperature=0.9,
            )
            return completion.choices[0].message
        
        message = await asyncio.to_thread(_blocking_call)

        # Append the full message object so the SDK can serialise it
        # correctly in follow-up turns.
        self._message_list.append(message)
        return message.content
    
    # ------------------------------------------------------------------
    # AIService interface — conversation
    # ------------------------------------------------------------------

    def set_prompt(self, prompt_text: str) -> None:
        """Reset history and set a new system prompt.
 
        Clears any previous conversation so the AI starts fresh with the
        provided system instruction.
 
        Args:
            prompt_text: System-level instruction for the AI.
        """
        self._message_list.clear()
        self._message_list.append({"role": "system", "content": prompt_text})
        logger.debug("Prompt set, history cleared.")

    
    async def send_question(self, prompt_text: str, message_text: str) -> str:
        """Send a one-shot question independently of the current history.
 
        The history is cleared and replaced with this prompt + question,
        so it is suitable for features like "random fact" where context
        from a previous conversation is irrelevant.
 
        Args:
            prompt_text:  System prompt for this specific call.
            message_text: The user's question.
 
        Returns:
            The AI's plain-text response.
        """
        self._message_list.clear()
        self._message_list.append({"role": "system", "content": prompt_text})
        self._message_list.append({"role": "user", "content": message_text})
        logger.debug("One-shot question set up, sending...")
        return await self._complete()
    
    async def add_message(self, message_text: str) -> str:
        """Append a user message to the ongoing conversation.
 
        Builds up multi-turn dialogue. Each call grows ``_message_list``
        so the AI has full context when generating its reply.
 
        Args:
            message_text: The user's message.
 
        Returns:
            The AI's plain-text response.
        """
        self._message_list.append({"role": "user", "content": message_text})
        logger.debug("User message added to history, sending...")
        return await self._complete()
    
    # ------------------------------------------------------------------
    # AIService interface — voice
    # ------------------------------------------------------------------

    async def speech_to_text(self, audio_path: str) -> str:
        """Transcribe an audio file using OpenAI Whisper.
 
        The file is opened and sent to the Whisper API. The blocking I/O
        is run in a thread pool to keep the event loop free.
 
        Args:
            audio_path: Path to the audio file (e.g. a .mp3 downloaded
                        from Telegram).
 
        Returns:
            The transcribed text.
 
        Note:
            This feature requires an OpenAI key with Whisper access.
            It is not available on Groq's free tier, so when using Groq
            the voice feature will raise a ``NotImplementedError``.
        """
        if not Path(audio_path).exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        def _blocking_call() -> str:
            with open(audio_path, "rb") as audio_file:
                transcription = self._client.audio.transcriptions.create(
                    model = "whisper-1",
                    file=audio_file,
                    response_format="text",
                )
            return transcription
        
        logger.debug("Transcribing audio: %s", audio_path)
        return await asyncio.to_thread(_blocking_call)
    
    async def text_to_speech(self, text: str, output_path: str) -> None:
        """Synthesise speech from text using OpenAI TTS and save to a file.
 
        The blocking API call and file write are both run in a thread pool.
 
        Args:
            text:        The text to convert to speech.
            output_path: Destination path for the generated .mp3 file.
                         Using a per-user path (e.g. ``"voice_<chat_id>.mp3"``)
                         is strongly recommended to avoid file collisions when
                         multiple users send voice messages simultaneously.
 
        Note:
            This feature requires an OpenAI key with TTS access and is not
            available on Groq's free tier.
        """
        def _blocking_call() -> None:
            response = self._client.audio.speech.create(
                model="tts-1",
                input=text,
                voice="alloy",  # "alloy" is the default voice, but you can specify others if your key has access
            )
            response.stream_to_file(output_path)

        logger.debug("Synthesising speech → %s", output_path)
        await asyncio.to_thread(_blocking_call)
    
    # ------------------------------------------------------------------
    # AIService interface — vision
    # ------------------------------------------------------------------

    async def recognize_image(self, image_path: str) -> str:
        """Describe an image using GPT-4o vision capabilities.
 
        The image is read from disk, base64-encoded, and sent to the API
        as an inline data URL. The blocking I/O is run in a thread pool.
 
        Args:
            image_path: Path to the image file (JPEG or PNG recommended).
                        Must be under 10 MB to comply with API limits.
 
        Returns:
            A natural-language description of the image contents.
 
        Note:
            Vision requires a model with image support (e.g. ``gpt-4o-mini``
            or ``gpt-4o``). LLaMA-based Groq models currently do not support
            image input, so this method will fail if called with a Groq backend.
        """
        if not Path(image_path).exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        def _encode_and_call() -> str:
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode("utf-8")

            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "user", 
                        "content": [
                            {
                                "type": "text",
                                "text": "Що на цьому зображенні?",
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                },
                            }
                        ]
                    },
                ],
            )
            return response.choices[0].message.content
        
        logger.debug("Recognizing image: %s", image_path)
        return await asyncio.to_thread(_encode_and_call)