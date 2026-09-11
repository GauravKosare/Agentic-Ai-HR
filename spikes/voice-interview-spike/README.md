# Phase 5 Voice Spike — scaffold

Disposable-quality prototype for the two-week timeboxed spike described in
[docs/spikes/phase5-voice-spike.md](../../docs/spikes/phase5-voice-spike.md). The deliverable is
the **measurements** (latency, STT/TTS quality per language, go/no-go writeup), not this code —
none of it is meant to survive into Phase 5 proper as-is.

Everything here is zero-cost: LiveKit self-hosted (Docker), Silero VAD (local), Groq Whisper STT
(reuses the already-built free-tier connector), the LLM Router (reuses the already-built
Gemini→Groq free-tier connector), Piper TTS (local, open source).

## Layout

```
spikes/voice-interview-spike/
├── docker-compose.yml     ← self-hosted LiveKit server + Redis, dev-mode API key/secret
├── requirements.txt       ← this spike's own venv, separate from src/backend's
├── .env.example
├── groq_stt_plugin.py     ← wraps app/connectors/speech_to_text.py as a LiveKit STT plugin
├── piper_tts_plugin.py    ← wraps local Piper inference as a LiveKit TTS plugin
├── interview_script.py    ← the fixed 3–4 question script used for days 5–10 (no adaptive logic)
└── agent.py               ← the LiveKit Agents worker wiring VAD → STT → LLM Router → TTS
```

API note: `agent.py`'s LiveKit wiring (`AgentServer` + `@server.rtc_session()`,
`stt.STT`/`tts.TTS` subclassing, `StopResponse`) was checked against livekit-agents' public
docs/source on 2026-09-11. This is a fast-moving framework — if `pip install` pulls a version
whose API has since shifted, fix the wiring against whatever actually installs rather than
assuming this file is gospel.

## Setup

1. **Start LiveKit locally** (or on the Oracle VM once past day 2):
   ```bash
   docker compose up -d
   ```
   This runs LiveKit server in dev mode on `ws://localhost:7880` with a fixed dev API
   key/secret (see `docker-compose.yml` — **dev-mode secrets only, never use these for anything
   with real candidate data**).

2. **This spike's own Python environment** (kept separate from `src/backend`'s venv so an
   unstable spike dependency can never touch the main backend):
   ```bash
   cd spikes/voice-interview-spike
   python -m venv .venv
   .venv\Scripts\activate          # Windows
   pip install -r requirements.txt
   ```

3. **Download Piper voices** into `voices/` (English first — see "Marathi, deferred" below
   for Hindi/Marathi sequencing):
   ```bash
   python -m piper.download_voices en_US-lessac-medium --data-dir voices/
   python -m piper.download_voices hi_IN-pratham-medium --data-dir voices/
   ```
   `PiperVoice.load()` takes a path to the downloaded `.onnx` file — `.env`'s
   `PIPER_VOICE_*_PATH` vars should point at `voices/<name>.onnx`.

   **Marathi, deferred by request (2026-09-11):** we're proving the LiveKit pipeline
   mechanics first (days 1–6, English) before spending time on Marathi voice sourcing.
   `PIPER_VOICE_MR_PATH` stays blank until then — `agent.py` fails fast with a clear message
   if you try to run `SPIKE_LANGUAGE=mr` before it's set, rather than silently falling back
   to another language. When you do pick it up: check Piper's voice list for an `mr_IN`
   entry first; if none exists at usable quality, that's the real spike finding the plan doc
   anticipates, and AI4Bharat Indic Parler-TTS/IndicF5 (already the documented fallback) is
   the next thing to try, not a sign the plugin wiring is wrong.

4. **Copy `.env.example` to `.env`** and fill in:
   - `LIVEKIT_URL` / `LIVEKIT_API_KEY` / `LIVEKIT_API_SECRET` — match `docker-compose.yml` for
     local dev.
   - `GROQ_API_KEY`, `GEMINI_API_KEY` — the same free-tier keys already used by `src/backend`
     (this spike imports those connectors directly; it does not duplicate the key handling).

5. **Run the agent worker:**
   ```bash
   python agent.py dev
   ```

6. **Join a room to talk to it** — LiveKit's hosted `agents-playground` (free, browser-based,
   no install) is the fastest way to get a mic/speaker UI pointed at a local LiveKit server
   during this spike; swap for a purpose-built join page only if the spike goes "go."

## What to actually measure, per day

See the day-by-day table in the plan doc. Keep a running log (a plain markdown file is fine) of:
- timestamp of each turn, and the speak→respond latency for it
- which language was being tested
- STT output vs. what was actually said (for WER spot-checks)
- subjective TTS intelligibility (1–5) per language
- anything that broke, hung, or produced a nonsensical turn

## Known limitations baked into this scaffold (by design — they're what days 3–10 test)

- STT is request/response per utterance (Groq Whisper), not a streaming API — the agent buffers
  audio between VAD-detected speech start/end and sends it as one chunk. If this is too slow for
  natural turn-taking, that itself is a spike finding, not a bug to silently fix here.
- The interview script is fixed and linear (`interview_script.py`) — no adaptive follow-up
  logic. That's Phase 5 proper, contingent on a "go."
- No disclosure/consent step, no transcript persistence, no scorecard. Out of scope per the plan
  doc's non-goals.
