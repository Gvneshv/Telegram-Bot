## A new temporary README file with the new project tree structure so far

```
project/
├── main.py                  ← entry point, builds and runs the app
├── config.py                ← loads tokens from env vars
├── handlers/
│   ├── commands.py          ← start, random, gpt, talk, quiz, etc.
│   ├── callbacks.py         ← all CallbackQueryHandlers
│   └── messages.py          ← text/voice/photo MessageHandlers
├── services/
│   └── gpt_service.py       ← ChatGptService (cleaned up)
├── utils/
│   ├── messaging.py         ← send_text, send_image, etc.
│   └── resources.py         ← load_message, load_prompt
├── state.py                 ← DialogState class (instance attributes, not class-level)
├── resources/
│   ├── images/
│   ├── messages/
│   └── prompts/
├── .env                     ← secrets (not committed)
├── .env.example             ← template (committed)
├── .gitignore
├── Dockerfile
└── requirements.txt
```