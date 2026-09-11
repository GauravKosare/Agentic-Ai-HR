# Phase 5 Voice Spike — Plan

*Per the [whole-project LLM Council verdict](../decisions/council-report-20260910-205930.html)
(2026-09-10): "the one thing to do first." This spike runs **before** Phase 2 (Distribution &
Response Monitoring), out of implementation-plan order, specifically to de-risk the item every
advisor flagged as most likely to fail.*

## Why this exists

[05-Implementation-Plan.md](../05-Implementation-Plan.md) originally planned the live interview
around a custom Playwright/Chromium bot joining Zoom/Meet through its browser web-join URL, with
OS-level virtual audio routing (PulseAudio/PipeWire loopback) connecting the meeting's audio to
Chrome's `SpeechRecognition`/`speechSynthesis`. The council's Executor advisor called this a
"rabbit hole" — 6–8 weeks before you even know if it works, on an undocumented browser API with
no server-side SLA, against a platform that actively fights bots.

**This spike replaces that approach.** Instead of joining someone else's meeting room and
scraping its audio, the interview runs in a WebRTC room we control (LiveKit, self-hosted, open
source, Apache 2.0 — no per-minute fee at any scale). The candidate gets a join link to *our*
page, not a Zoom/Meet link. This sidesteps the entire OS-audio-routing problem and Zoom's bot
detection, at the cost of dropping the "meet the candidate where they already are" idea — a
trade the council's Executor and First Principles advisors both endorsed.

## What this spike proves or kills

A **hard go/no-go at day 14** on: *can a fully zero-cost, self-hosted voice pipeline hold a
real-time conversational interview in English, Hindi, and Marathi at acceptable latency and
speech quality?*

Not in scope for the spike: the adaptive interview logic (resume-grounded follow-ups), the
disclosure/consent flow, scoring, or any Owner Console integration. Those are Phase 5/6 proper,
and only worth building if this spike is a "go."

## Zero-cost component stack

| Piece | Choice | Why |
|---|---|---|
| Real-time room / SFU | **LiveKit**, self-hosted (Docker) | Open source, Apache 2.0, no usage fee when self-hosted. Runs on the Oracle Cloud Always Free VM already provisioned for Phase 5. |
| Voice activity detection | **Silero VAD** (`livekit-plugins-silero`) | Open source, runs locally, no API call. |
| Speech-to-text | **Groq-hosted Whisper chain** (already built — `speech_to_text.py`) | Reuses the connector verified in Phase 0. Free tier, LPU-accelerated. Known limitation for this use: it's request/response, not streaming — the spike measures whether chunked-utterance STT is fast enough for real-time turn-taking, or whether it forces a push-to-talk-style interaction instead. |
| Language model (interview dialogue) | **LLM Router** (already built — `llm_router.py`, `Task.INTERVIEW_DIALOGUE`) | Reuses the connector verified in Phase 0/1. Zero paid-model risk already handled. |
| Text-to-speech | **Piper**, self-hosted (open source, local ONNX inference) | Free, runs offline, no API key. Has community voices for `hi_IN`; Marathi coverage is unverified going in — **this spike is what verifies it.** AI4Bharat Indic Parler-TTS/IndicF5 stays the documented fallback if Piper's Hindi/Marathi quality doesn't clear the bar. |

This is a genuinely different pipeline from the original Chrome-Web-Speech-API plan — it trades
"free because it's the browser's built-in feature" for "free because every component is
self-hosted open source," which fits the project's zero-cost policy either way and removes the
undocumented-API risk.

## Day-by-day plan (2 weeks)

| Days | Goal |
|---|---|
| 1–2 | Stand up self-hosted LiveKit server (Docker Compose, provided in `spikes/voice-interview-spike/`). Confirm two browser tabs can join the same room and hear each other — proves the room mechanics work before any AI is involved. |
| 3–4 | Wire the agent worker: Silero VAD → Groq Whisper STT → fixed scripted response (no LLM yet) → Piper TTS, English only. Goal: hear the bot say a canned sentence back after you speak. Proves the four components chain together at all. |
| 5–6 | Swap the fixed response for `llm_router.generate(..., Task.INTERVIEW_DIALOGUE)` with a short fixed interview script (3–4 questions, no adaptive follow-ups yet). Measure end-to-end latency (speak → hear response) across ~10 turns. |
| 7–8 | Hindi and Marathi: STT accuracy (Groq Whisper's multilingual support), Piper voice availability/quality, code-switching within a sentence. This is the highest-uncertainty pair of days — the council flagged this as unvalidated. |
| 9–10 | Adversarial testing: interruptions, silence/thinking pauses, background noise, a bad/flaky connection, an off-script answer. These are the failure modes the Outsider advisor specifically called out as where a live interview breaks in the real world. |
| 11–12 | Buffer for whatever day 1–10 surfaced. Write up numbers, not impressions: measured latency (p50/p90), STT word-error-rate spot check per language, TTS intelligibility per language (subjective 1–5 rating from a few test listeners). |
| 13–14 | Go/no-go writeup (below) + decision. |

## Go/no-go criteria

Write actual measured numbers against each line — this is a decision document, not a vibe check.

- [ ] End-to-end latency (speak → hear response) — target ~2–3s is tolerable for a screening
      interview (looser than the original ~1s target, which assumed a snappier browser-native
      path); record the actual p50/p90 across all three languages.
- [ ] STT is usably accurate in English / Hindi / Marathi, including common code-switching
      patterns, on real (not scripted-clean) speech.
- [ ] Piper TTS voice quality is acceptable in Hindi and Marathi, or AI4Bharat fallback closes
      the gap without breaking the zero-cost/self-hosted constraint.
- [ ] The pipeline recovers gracefully from a dropped/re-joined connection, silence, and
      interruption — doesn't hang or corrupt the conversation state.
- [ ] Self-hosted LiveKit + Piper run acceptably on the Oracle Always Free VM's actual resource
      ceiling (2 OCPU/12GB at time of writing) under one concurrent interview.

**Go** — all of the above clear the bar (numbers, not "seemed fine") → proceed to build the real
interview logic agent, disclosure step, and Owner Console integration per Phase 5/6.

**No-go** — proceed with the council's fallback: **asynchronous recorded screening.** The
candidate records answers to a fixed question set (webcam/mic in the browser, no real-time
pipeline required); Groq Whisper transcribes after the fact; the LLM Router scores it. Same
signal to the recruiter, none of the real-time-latency or turn-taking risk, ships in a fraction
of the time. This isn't a consolation prize — the council's First Principles advisor argued it's
plausibly the *better* design regardless of whether the live pipeline works.

## Non-goals for this spike

- No candidate PII enters this spike. Test with the builder's own voice/a colleague's, not real
  applicant data — this runs before the DPIA/compliance-scope question (also flagged by the
  council) is resolved.
- No production error handling, retries, or persistence. The scaffold in
  `spikes/voice-interview-spike/` is disposable-quality by design; only the *measurements* it
  produces are the deliverable.
