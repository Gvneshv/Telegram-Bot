"""
Abstract base class (interface) for all AI service implementations.
 
Every AI provider — OpenAI, Groq, Gemini, etc. — must implement this
interface. This means the rest of the bot (handlers, commands) only ever
talks to an ``AIService`` and never to a provider-specific class directly.
Swapping or adding a provider in the future therefore requires no changes
outside of this ``services/`` package.
 
Design pattern: this is a *Strategy* pattern. The particular service
(e.g. ``OpenAIService``) is the strategy; the bot handlers are the context
that uses it.
"""

from abc import ABC, abstractmethod

class AIService(ABC):
    """Defines the contract that every AI backend must fulfil.
 
    Particular subclasses must implement all abstract methods below.
    They may also add provider-specific methods, but the bot will only
    call the ones defined here.
    """
 
    # ------------------------------------------------------------------
    # Conversation state
    # ------------------------------------------------------------------

    @abstractmethod
    def set_prompt(self, prompt_text: str) -> None:
        """Reset the conversation and set a new system prompt.
 
        Clears any prior message history so the next exchange starts
        fresh with the given system instruction.
 
        Args:
            prompt_text: The system-level instruction for the AI
                         (e.g. "You are Kurt Cobain. Answer in character.").
        """

    @abstractmethod
    def send_question(self, prompt_text: str, message_text: str) -> str:
        """Send a one-shot question with its own prompt, ignoring history.
 
        Useful for stateless calls like "give me a random fact" where
        conversation context is irrelevant.
 
        Args:
            prompt_text:  System prompt for this specific question.
            message_text: The user's question.
 
        Returns:
            The AI's plain-text response.
        """
    
    @abstractmethod
    def add_message(self, message_text: str) -> str:
        """Append a user message to the history and get a response.
 
        Builds up a multi-turn conversation. Each call appends the user
        message and the assistant reply to the internal history, so
        subsequent calls have full context.
 
        Args:
            message_text: The user's message.
 
        Returns:
            The AI's plain-text response.
        """
    
    # ------------------------------------------------------------------
    # Voice (optional — not all providers support this)
    # ------------------------------------------------------------------

    @abstractmethod
    async def speech_to_text(self, audio_path: str) -> str:
        """Transcribe an audio file to text.
 
        Args:
            audio_path: Path to the audio file on disk (e.g. an .mp3
                        downloaded from Telegram).
 
        Returns:
            The transcribed text.
 
        Raises:
            NotImplementedError: If the provider does not support STT.
        """
    
    @abstractmethod
    async def text_to_speech(self, text: str, output_path: str) -> None:
        """Convert text to speech and write the result to a file.
 
        Args:
            text:        The text to synthesise.
            output_path: Destination file path (e.g. "answer.mp3").
 
        Raises:
            NotImplementedError: If the provider does not support TTS.
        """
    
    # ------------------------------------------------------------------
    # Vision (optional — not all providers support this)
    # ------------------------------------------------------------------

    @abstractmethod
    async def recognize_image(self, image_path: str) -> str:
        """Describe or analyse an image file.
 
        Args:
            image_path: Path to the image file on disk.
 
        Returns:
            A natural-language description of the image.
 
        Raises:
            NotImplementedError: If the provider does not support vision.
        """