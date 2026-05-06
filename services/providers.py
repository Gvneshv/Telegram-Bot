"""
Provider registry — all supported AI backends in one place.

To add a new provider:
  1. Add a new ProviderConfig entry to PROVIDERS.
  2. Add its API key env var to '.env.example'.
  3. Nothing else needs to change.
"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderConfig:
    key: str    # Internal identifier, e.g. "groq"
    label: str  # Button label shown to user
    callback_data: str  # Callbakc data for the selection button
    api_key_env: str    # Name of the env var holding the API key
    default_model: str  # Default model when AI_MODEL is not overridden
    base_url: str | None   # None -> OpenAI SDK default (api.openai.com)
    supports_voice: bool
    supports_vision: bool
    unavailable_note: str   # Short note shown in alert when provider is locked


# All providers the bot knows about, in display order.
PROVIDERS: list[ProviderConfig] = [
    ProviderConfig(
        key="groq",
        label="⚡ Groq  (LLaMA 3.3 · безкоштовно)",
        callback_data="model_groq",
        api_key_env="GROQ_API_KEY",
        default_model="llama-3.3-70b-versatile",
        base_url="https://api.groq.com/openai/v1",
        supports_voice=False,
        supports_vision=False,
        unavailable_note="Groq недоступний: ключ GROQ_API_KEY не налаштовано.",
    ),
    ProviderConfig(
        key="openai",
        label="🧠 OpenAI  (GPT-4o · голос + зображення)",
        callback_data="model_openai",
        api_key_env="OPENAI_API_KEY",
        default_model="gpt-4o-mini",
        base_url=None,
        supports_voice=True,
        supports_vision=True,
        unavailable_note="OpenAI недоступний: ключ OPENAI_API_KEY не налаштовано.",
    ),
    ProviderConfig(
        key="gemini",
        label="✨ Google Gemini  (Flash 2.5 · безкоштовно · зображення)",
        callback_data="model_gemini",
        api_key_env="GEMINI_API_KEY",
        default_model="gemini-2.5-flash",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        supports_voice=False,
        supports_vision=True,
        unavailable_note="Gemini недоступний: ключ GEMINI_API_KEY не налаштовано.",
    ),
]


def get_provider(key: str) -> ProviderConfig | None:
    """
    Return the ProviderConfig for the given key, or None.
    """
    return next((p for p in PROVIDERS if p.key == key), None)


def available_providers() -> list[ProviderConfig]:
    """
    Providers for which an API key is present in the environment.
    """
    return [p for p in PROVIDERS if os.getenv(p.api_key_env)]


def unavailable_providers() -> list[ProviderConfig]:
    """
    Providers that are defined but have no API key configured.
    """
    return [p for p in PROVIDERS if not os.getenv(p.api_key_env)]