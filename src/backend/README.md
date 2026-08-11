# Backend — Setup

Foundation connectors so far: **Supabase**, the **LLM Router** (Gemini → Groq, TRD §3.1a), and **Speech-to-Text** (Groq-hosted Whisper, now a fallback behind Chrome's in-browser `SpeechRecognition` per TRD §3.7). Later phases add Brevo, Zoom, Google Meet, and the custom Playwright/Chromium meeting-bot pipeline — see [05-Implementation-Plan.md](../../docs/05-Implementation-Plan.md).

## Setup

```bash
cd src/backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt

copy .env.example .env        # then open .env and fill in your real keys
```

Fill in `.env` yourself, directly in a text editor — never paste real API keys into a chat session with an AI assistant, including this one.

Where to get each key is commented in [.env.example](./.env.example):
- **Supabase** — Project Settings → API Keys in your Supabase dashboard. Use the new **Secret key** (`sb_secret_...`) for `SUPABASE_SECRET_KEY`, not the legacy `service_role` JWT — same permissions, but it rotates independently if it ever leaks. The **Publishable key** (`sb_publishable_...`) is optional for now; nothing needs it yet.
- **Gemini** — [aistudio.google.com](https://aistudio.google.com) → Get API key. Leave billing **disabled** on the project, or the free tier disappears.
- **Groq** — [console.groq.com](https://console.groq.com) → API Keys.

## Verify everything is wired up

```bash
python -m scripts.check_connectors
```

This calls each service with the smallest possible request (Supabase: list one user via the admin API; LLM Router: a one-word completion) and reports pass/fail per connector — it never prints your actual key values.

## Layout

```
src/backend/
├── app/
│   ├── core/config.py           ← env var loading (pydantic-settings)
│   └── connectors/
│       ├── supabase_client.py   ← service-role client (backend) + anon client (RLS testing)
│       └── llm_router.py        ← Gemini primary / Groq fallback / quota-pause (TRD §3.1a)
├── scripts/check_connectors.py  ← run after filling in .env
├── tests/
├── requirements.txt
└── .env.example
```
