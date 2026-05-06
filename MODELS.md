# AI Models & Feature Support

This bot supports multiple AI providers. The provider is chosen by the user
at startup and can be changed at any time via /model.

## Provider comparison

| Feature              | Groq (LLaMA 3.3) | OpenAI (GPT-4o-mini) | Gemini (Flash 2.5) |
|----------------------|:----------------:|:--------------------:|:------------------:|
| GPT Chat             | ✅               | ✅                   | ✅                 |
| Random Fact          | ✅               | ✅                   | ✅                 |
| Talk (personas)      | ✅               | ✅                   | ✅                 |
| Quiz                 | ✅               | ✅                   | ✅                 |
| Translator           | ✅               | ✅                   | ✅                 |
| Recommendations      | ✅               | ✅                   | ✅                 |
| CV Generator         | ✅               | ✅                   | ✅                 |
| Voice Chat (STT+TTS) | ❌               | ✅                   | ❌                 |
| Image Recognition    | ❌               | ✅                   | ✅                 |
| Cost                 | Free             | Paid                 | Free (20 req/day)  |
| Speed                | Very fast        | Medium               | Fast               |

## Adding a new provider

The bot uses OpenAI-compatible APIs. Any provider that supports this
interface can be added with ~5 lines in `services/providers.py`
and one route entry in `handlers/callbacks.py`.

**Candidates for the future:**
- **Mistral** — affordable, good quality text.
  Env var: `MISTRAL_API_KEY`. Endpoint: `api.mistral.ai`