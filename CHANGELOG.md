# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versions follow [Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH`.

A **MAJOR** bump means a breaking change or complete architectural rewrite.
A **MINOR** bump means a new feature added in a backward-compatible way.
A **PATCH** bump means a bug fix with no behaviour change from the user's perspective.

---

## [2.0.0] — in development

Complete architectural rewrite. The bot's behaviour from the user's perspective
is unchanged, but every internal system has been reworked to fix critical bugs
and establish a clean, maintainable structure.

### Fixed

- **Critical: shared global state.** In v1, a single `Dialog` object and a single
  `ChatGptService` instance were shared across all users simultaneously. Any two
  users interacting with the bot at the same time would corrupt each other's state —
  one user's message could be routed into another user's quiz, and their messages
  would be mixed into the same AI conversation history.
  Fixed by storing per-user `DialogState` and `AIService` instances inside
  `context.user_data`, which `python-telegram-bot` isolates per user automatically.

- **Critical: `if` instead of `elif` in message router.** The original
  `handle_message` used a chain of plain `if` statements, meaning multiple
  handlers could fire for a single message. All branches are now `elif`.

- **Critical: hardcoded temp filenames cause file collisions.** Voice and image
  files were saved to `user_voice.mp3`, `answer.mp3`, and `image.jpg` — shared
  filenames that two concurrent users would overwrite each other's files into.
  Fixed by using chat-ID-scoped filenames (e.g. `voice_123456_input.mp3`).

- **Blocking async calls freeze the event loop.** The original `speech_to_text`
  and `text_to_speech` were marked `async` but called the synchronous OpenAI SDK
  directly, blocking the event loop and freezing the bot for all users while one
  person's voice message was processing.
  Fixed by wrapping all blocking SDK calls with `asyncio.to_thread()`.

- **Redundant `client` parameter on service methods.** Methods that already had
  access to `self.client` also accepted `client` as a parameter. Removed.

- **Dead code in `util.py`.** `dialog_user_info_to_str()` was never called, and
  the `default_callback_handler` in `util.py` was shadowed by one in `bot.py`.
  A `lambda k, v` in a `map()` call would also have raised `TypeError` at runtime.
  All removed.

- **`credentials.py` committed to the repo.** Secrets now live in `.env`
  (never committed). `.env.example` serves as the committed template.

### Changed

- **Project structure.** Monolithic `bot.py` (562 lines) split into focused modules:
  `handlers/commands.py`, `handlers/callbacks.py`, `handlers/messages.py`,
  `main.py`, `state.py`, `config.py`, `services/`, `utils/`.

- **Dependency management.** `requirements.txt` (hand-maintained) replaced by
  Poetry (`pyproject.toml` + `poetry.lock`) for local development, with
  `requirements.txt` generated automatically via `poetry export` for Docker.

- **Docker.** Single-stage Dockerfile replaced by a multi-stage build (builder +
  runtime). Added `docker-compose.yml` with env injection, resource volume mount,
  memory limits, and healthcheck. Added `.dockerignore`.

- **Repetitive if/elif chains replaced by dispatch tables.** Quiz topics,
  translation languages, and historical personas are now dictionaries.
  Adding a new quiz topic or language is a one-line change.

- **Five separate callback handler functions replaced by a single dispatcher**
  with a flat `_ROUTES` table in `handlers/callbacks.py`.

- **Five separate persona functions replaced by a single `start_persona()` helper**
  driven by the `PERSONAS` constant. Adding a new persona is one dict entry
  plus two resource files.

### Added

- `services/base.py` — abstract `AIService` interface. Any new AI provider
  (Gemini, Ollama, etc.) implements this interface; nothing else needs to change.
- `services/factory.py` — builds the correct service from environment config.
- Groq support — set `AI_PROVIDER=groq` for a free OpenAI-compatible backend.
- `config.log_config_summary()` — logs active provider, model, and base URL at startup.
- `state.DialogState.reset()` — cleanly resets all user state when returning to main menu.
- Graceful error messages for voice and image features when using a provider
  that does not support them (e.g. Groq).
- Docstrings on every module, class, and function.
- `ruff`, `mypy`, and `pytest` configured in `pyproject.toml`.

### Removed

- `bot.py` — replaced by `handlers/`, `main.py`.
- `gpt.py` — replaced by `services/`.
- `util.py` — replaced by `utils/messaging.py` and `utils/resources.py`.
- `credentials.py` — replaced by `config.py` + `.env`.
- Original `requirements.txt` — replaced by Poetry-managed dependency workflow.

---

## [1.0.0] — initial release

First working version of the bot. Single-file implementation across `bot.py`,
`gpt.py`, and `util.py`. Supports all nine features (random facts, GPT chat,
persona dialogues, quiz, translator, voice chat, recommendations, image
recognition, CV generator).

Known issues carried into v2.0.0: shared global state, blocking async calls,
hardcoded temp filenames, dead code, credentials committed to the repo.