# AI Models & Feature Support

This bot supports multiple AI providers. The provider is chosen by the user
at startup and can be changed at any time via /model.

## Provider comparison

| Feature              | Groq (LLaMA 3.3) | OpenAI (GPT-4o-mini) |
|----------------------|:----------------:|:--------------------:|
| GPT Chat             | ✅               | ✅                   |
| Random Fact          | ✅               | ✅                   |
| Talk (personas)      | ✅               | ✅                   |
| Quiz                 | ✅               | ✅                   |
| Translator           | ✅               | ✅                   |
| Recommendations      | ✅               | ✅                   |
| CV Generator         | ✅               | ✅                   |
| Voice Chat (STT+TTS) | ❌               | ✅                   |
| Image Recognition    | ❌               | ✅                   |
| Cost                 | Free             | Paid                 |
| Speed                | Very fast        | Medium               |

## Adding a new provider

The bot uses OpenAI-compatible APIs. Any provider that supports this
interface can be added with ~5 lines:

1. Add a `ProviderConfig` entry in `services/providers.py`.
2. Add the API key env var to `.env.example`.
3. Uncomment the matching route in `handlers/callbacks.py`.

**Candidates already prepared in the code (commented out):**
- **Google Gemini** — free tier, vision support, very fast.
  Env var: `GEMINI_API_KEY`. Endpoint: `generativelanguage.googleapis.com`
- **Mistral** — affordable, good quality text.
  Env var: `MISTRAL_API_KEY`. Endpoint: `api.mistral.ai`