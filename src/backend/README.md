# Backend — Setup

Connectors so far: **Supabase**, the **LLM Router** (Gemini → Groq, TRD §3.1a), **Speech-to-Text** (Groq-hosted Whisper, now a fallback behind Chrome's in-browser `SpeechRecognition` per TRD §3.7), **Email** (Brevo, TRD §3.5), and **Zoom** (Server-to-Server OAuth, TRD §3.6). Remaining: Google Meet, and the custom Playwright/Chromium meeting-bot pipeline — see [05-Implementation-Plan.md](../../docs/05-Implementation-Plan.md).

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
- **Supabase** — Project Settings → API Keys in your Supabase dashboard. Use the new **Secret key** (`sb_secret_...`) for `SUPABASE_SECRET_KEY`, not the legacy `service_role` JWT — same permissions, but it rotates independently if it ever leaks. The **Publishable key** (`sb_publishable_...`) is optional for now; nothing needs it yet. Free Supabase projects **auto-pause after 1 week of inactivity** — if the connector fails with a DNS-resolution error, check the project isn't paused before assuming the code is broken.
- **Gemini** — [aistudio.google.com](https://aistudio.google.com) → Get API key. Leave billing **disabled** on the project, or the free tier disappears.
- **Groq** — [console.groq.com](https://console.groq.com) → API Keys.
- **Brevo** — dashboard → Settings → SMTP & API → API Keys. `BREVO_SENDER_EMAIL` must be a verified sender in your account.
- **Zoom** — [marketplace.zoom.us](https://marketplace.zoom.us) → Develop → Build App → **Server-to-Server OAuth** (not the retired JWT type). Add scopes `meeting:write:meeting` + `meeting:read:meeting`, activate, then copy Account ID / Client ID / Client Secret from App Credentials.

## Verify everything is wired up

```bash
python -m scripts.check_connectors
```

Calls each service with the smallest possible request (Supabase: list one user via the admin API; LLM Router / STT: a one-word/half-second request; Email: an account read, no send; Zoom: fetch an OAuth token, no meeting created) and reports pass/fail per connector — it never prints your actual key values.

## Layout

```
src/backend/
├── app/
│   ├── core/config.py            ← env var loading (pydantic-settings)
│   └── connectors/
│       ├── supabase_client.py    ← service-role client (backend) + anon client (RLS testing)
│       ├── llm_router.py         ← Gemini primary / Groq fallback / quota-pause (TRD §3.1a)
│       ├── speech_to_text.py     ← Groq-hosted Whisper (STT fallback, TRD §3.7)
│       ├── email.py              ← Brevo transactional email (TRD §3.5)
│       ├── zoom.py               ← Zoom Server-to-Server OAuth, meeting creation (TRD §3.6)
│       └── _shared.py            ← quota-error detection + chain-walking, used by llm_router & speech_to_text
├── scripts/check_connectors.py   ← run after filling in .env
├── tests/
├── requirements.txt
└── .env.example
```
