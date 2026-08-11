# Financial & Subscription Tracking Document
## AI Recruiter Agent — Conversational Agentic Hiring Assistant

**Version:** 2.3 — Meeting bot switched from Vexa to a custom Playwright/Chromium bot; STT/TTS primary switched to Chrome's in-browser Web Speech APIs, with Groq Whisper/AI4Bharat kept as fallbacks
**Date:** July 20, 2026
**Purpose:** A living inventory of every third-party tool/service this project uses — what it's for, where it's used, how much we use it, whether it's free, and what it costs if it isn't. **Project policy: free-tier-only, zero recurring cost, for the development/pilot stage.** Any tool without a viable free path was replaced; where no drop-in free replacement existed, the system was designed to degrade gracefully (pause) instead of spending.

**Baseline usage assumption** (per [01-PRD.md §11](./01-PRD.md)): pilot/MVP scale = dozens to low-hundreds of candidates per requisition, a handful of requisitions active at once, single Owner account.

---

## 1. Status Legend

| Symbol | Meaning |
|---|---|
| ✅ | Free at our usage scale, no card required, no time-boxed trial |
| ⚠️ | Free tier covers pilot scale but has a real ceiling (a rate limit, not a spending limit) — the system degrades gracefully rather than incurring cost when the ceiling is hit; monitor before scaling past pilot |
| 🔁 | Was paid/uncertain in the original design; **replaced** with a free alternative |

*(As of this revision there are no 🔴 "no zero-cost path" items — see §4 for how each of the four originally-flagged items was resolved.)*

---

## 2. Full Tool Inventory

| Tool / Service | Category | Used By (Agent / Stage) | Usage at Pilot Scale | Free Tier Terms (verified July 2026) | What Happens If the Free Tier Is Hit | Status |
|---|---|---|---|---|---|---|
| **Supabase** | DB (Postgres+pgvector), Auth, Storage, Realtime | All agents; system of record | 1 project, low hundreds of rows/requisition | 500MB DB, 1GB storage, 5GB egress, 50,000 MAU, 500K edge fn calls, 2M realtime msgs/mo | Free project pauses after 1 week idle; would need Pro ($25/mo) only if DB/storage/egress ceiling is hit — unlikely at pilot scale | ✅ |
| **GitHub + GitHub Actions** | Source control, CI/CD | Whole repo, build/test pipelines | 1 private repo, low CI volume | Unlimited private repos; ~2,000 CI minutes/mo free | N/A at this scale | ✅ |
| **Vercel or Netlify** | Frontend hosting | React web app | Low traffic, single site | Hobby/free tier | N/A at this scale | ✅ |
| **Google Cloud Run or Render** | Backend API hosting (stateless paths only) | FastAPI/LangGraph orchestrator — requirement intake, form, distribution, notifications, scoring | 1 low-traffic service | Cloud Run: 2M requests/mo, 360K GB-seconds free. Render: free Web Service, sleeps after 15 min idle | Paid tier if traffic exceeds free allowance; Render's sleep is harmless here since these paths are request/response, not long-running | ✅ |
| **Oracle Cloud Always Free ARM VM** 🔁 | Persistent hosting for the meeting-bot pipeline | Custom Playwright/Chromium bot (runs Chrome's `SpeechRecognition`/`speechSynthesis` in-tab) + AI4Bharat TTS fallback, running together as one long-lived process per interview | 1 VM, one interview at a time at pilot scale | Permanent free ARM VM — **currently 2 OCPU/12GB RAM** (Oracle cut this from 4 OCPU/24GB in June 2026 with no announcement; verify actual allocation at signup) | No paid fallback needed at pilot scale; if concurrency or RAM needs grow, next step is a small paid VM, not Cloud Run/Render (wrong architecture for this workload) | ✅ (verify terms at signup — see residual risk in §5) |
| **Zoom API** | Instant meeting creation (primary) | Meeting Orchestration Agent | 1:1 bot+candidate calls, ≤30 min each | Free Basic account: unlimited 1:1 meetings, capped at 40 min/session | Only need paid Zoom if interview length is raised above 40 min — not planned | ✅ |
| **Google Meet API** | Fallback meeting creation | Meeting Orchestration Agent | Occasional fallback calls | Free with any Google account | N/A at this scale | ✅ |
| **Sentry** | Error monitoring | All backend/frontend error tracking | Low error volume | Developer tier: 5,000 errors/mo free | Paid tier if error volume scales | ✅ |
| **Grafana + Prometheus** | Metrics/monitoring | Backend observability | Self-hosted | Open source, free forever | N/A (only the compute it runs on has a cost, already covered above) | ✅ |
| **Brevo** 🔁 | Transactional email — now the **sole** candidate messaging channel | Notification Agent | Interview invites, confirmations, status updates; low hundreds/mo | 300 emails/day, permanently free | Paid tier beyond 300/day — very unlikely at pilot scale | ✅ |
| **Google Gemini API** 🔁 | Primary LLM — per-tier model CHAIN, not one model | LLM Router (TRD §3.1a) — nearly every agent | Highest-volume dependency | Reasoning chain: `gemini-3.5-flash` → `gemini-3-flash` (each ~20 RPD on a typical account, doubling the daily budget). Light chain: `gemini-3.1-flash-lite` (~500 RPD) → `gemma-4-26b`/`gemma-4-31b` (~14.4K RPD each). Resets 00:00 Pacific Time; free only while billing stays disabled. Per-model limits verified against a live account 2026-07-20 — these are account-specific and drift, re-check in Google AI Studio. | Router moves to the next model in the same chain first; only once the whole Gemini chain is exhausted does it fall through to Groq (below) | ✅ (rate-limited, not cost-limited) |
| **Groq API (LLM)** 🔁 | Fallback LLM — also a per-tier model CHAIN | LLM Router (TRD §3.1a) — triggered when Gemini's whole chain for that tier is exhausted | Fallback volume only | Reasoning chain: `openai/gpt-oss-120b` → `llama-3.3-70b-versatile` → `qwen/qwen3.6-27b` (each ~30 RPM/1,000 RPD, verified live 2026-07-20). Light chain: `openai/gpt-oss-20b` (~1,000 RPD) → `llama-3.1-8b-instant` (~14,400 RPD — by far the most generous single model in either provider's free tier, saved for last). No card, no expiry; Groq flagged `llama-3.3-70b-versatile`/`llama-3.1-8b-instant` for migration 2026-06-17 but both remained live with published quotas — re-verify at console.groq.com/docs/rate-limits. | Router pauses all AI-dependent actions and notifies the Owner once, only after every model in both chains is exhausted (TRD §3.1a) — no fallthrough to a paid model | ✅ (rate-limited, not cost-limited) |
| **Playwright (Chromium automation)** 🔁 | Meeting bot join — replaces Vexa (see §4b decision record) | Meeting Bot / Live Interview Agent | 1 bot session per interview | Open source (Apache License 2.0), self-hosted — no vendor account, no billing at all | N/A — runs on the Oracle Cloud VM above, no separate cost | ✅ |
| **Chrome `SpeechRecognition` / `speechSynthesis`** 🔁 | STT/TTS primary — in-browser, replaces Groq-hosted Whisper + AI4Bharat as the primary path (see §4b) | Meeting Bot / Live Interview Agent | Real-time audio, every interview minute | Built into Chromium — free, no API key, no account, no rate limit in the metered sense | N/A — runs inside the bot's own browser tab on the Oracle Cloud VM; **unvalidated risk**: headless-Linux voice quality/availability for Hindi/Marathi TTS, test in Phase 5 | ✅ (quality/validation risk, see §4b) |
| **Groq API (STT)** 🔁 | Speech-to-text — fallback only now (was primary, see §4b) | Meeting Bot / Live Interview Agent, `app/connectors/speech_to_text.py` (kept, not deleted) | Fallback volume only | Chain: `whisper-large-v3-turbo` → `whisper-large-v3`, each ~20 RPM/2,000 RPD/28.8K audio-seconds-per-day free, verified live 2026-07-20. Same `GROQ_API_KEY` as the LLM fallback above — demoting this to a fallback also demotes the correlated-outage risk with the LLM Router, since Groq is no longer in the primary STT path | Raises `TranscriptionUnavailable` if both models are exhausted — falls through to no STT for that turn, logged | ✅ (rate-limited, not cost-limited) |
| **AI4Bharat Indic Parler-TTS / IndicF5** 🔁 | TTS — fallback only now (was primary, see §4b) | Meeting Bot / Live Interview Agent | Fallback volume only | Open source, self-hosted, free | N/A — runs on the Oracle Cloud VM above; not yet latency-benchmarked (§4) | ✅ (quality trade-off, see §4) |
| **Claude (Anthropic API)** 🔁 removed | — | — | — | No ongoing free tier | Replaced entirely by the Gemini→Groq LLM Router | — |
| **Sarvam AI** 🔁 removed | — | — | — | No ongoing free tier | Replaced by Chrome in-browser STT/TTS, with Groq-hosted Whisper + self-hosted AI4Bharat as fallback | — |
| ~~Self-hosted Whisper (original design)~~ 🔁 removed | — | — | — | Ran on the Oracle VM, CPU-only, documented latency risk | Superseded by Groq-hosted Whisper, now itself demoted to fallback behind Chrome's in-browser STT — see §4a and §4b | — |
| **Recall.ai / MeetStream.ai** 🔁 removed | — | — | — | 5 free hours total, then per-minute billing | Replaced by self-hosted Vexa, itself later replaced by a custom Playwright bot — see §4b | — |
| ~~Vexa~~ 🔁 removed | — | — | — | Free/self-hosted, but abstracts away the browser — incompatible with using Chrome's own Web Speech APIs | Replaced by a custom Playwright/Chromium bot (see §4b) — the browser tab itself is now the bot, not something Vexa manages for us | — |
| **WhatsApp Business Cloud API** 🔁 removed | — | — | — | Business-initiated template messages billed per message, no zero-cost path | Removed — Email (Brevo) is now the sole candidate channel | — |
| ~~Affinda~~ | Resume parsing | — | — | No permanent free tier | Removed — resume parsing now runs through the LLM Router + open-source PyMuPDF/pdfplumber | — |
| ~~SendGrid~~ | Transactional email | — | — | Free plan discontinued (2025) | Replaced by Brevo | — |

---

## 3. How the Two Rate-Limited Items Are Handled (Gemini + Groq)

Gemini and Groq are the only two items in this stack with a hard usage ceiling on the free tier — everything else is either unlimited-at-our-scale or a one-time/self-hosted cost. Because both are *rate-limited* (a request-count cap), not *cost-limited* (a spending cap), there is no way to "accidentally" incur a bill from either one — hitting the ceiling simply returns an error (HTTP 429), which the LLM Router (TRD §3.1a) is built to handle:

1. Try Gemini (free tier).
2. On a 429, retry the same request against Groq (free tier).
3. On a 429 from Groq too, stop. Set an `ai_paused` flag, send the Owner one Email notification summarizing today's usage and the next reset time, and resume automatically when the quota clears — Gemini's daily quota resets at 00:00 Pacific Time; Groq's reset timing should be re-confirmed against current docs each time this section is revisited, since exact free-tier terms shift over time.

This is documented behavior, not a failure mode — see TRD §3.1a and §8 (Failure Handling) for the full spec.

## 4. Decision Record — How Each Originally-Flagged Item Was Resolved

The prior version of this document (v1.0) flagged four items with no zero-cost path at production quality: Claude (LLM), Sarvam AI (STT/TTS), Recall.ai/MeetStream.ai (meeting bot), and WhatsApp (messaging). All four have now been resolved per your direction, prioritizing $0 cost over capability where a trade-off was unavoidable:

| Item | Resolution | Trade-off accepted |
|---|---|---|
| **Claude (LLM)** | Replaced with a **Gemini-primary, Groq-fallback router** (§3 above), each provider a multi-model chain (§2); pauses gracefully rather than ever falling through to a paid model | Lower reasoning quality than Claude Sonnet for nuanced interview follow-ups/scoring justification; daily request caps may bind on a busy pilot day, causing a temporary pause |
| **Sarvam AI (STT/TTS)** | STT: **Groq-hosted Whisper** (`whisper-large-v3-turbo` → `whisper-large-v3` chain, LPU-accelerated, free — see §4a). TTS: **self-hosted AI4Bharat Indic Parler-TTS/IndicF5** on the Oracle Cloud Always Free VM | Materially weaker Hindi/Marathi code-switching accuracy than the purpose-built commercial option (a Whisper-family limitation regardless of hosting); TTS latency on the CPU-only Oracle VM not yet benchmarked; STT now shares Groq as a provider with the LLM fallback, a correlated-outage risk (§4a) |
| **Recall.ai / MeetStream.ai (meeting bot)** | Replaced with **self-hosted Vexa** (open source, Apache 2.0), on the same Oracle Cloud VM — an existing free/open-source project, not a from-scratch build | Self-hosting/ops responsibility shifts to the team instead of being handled by a managed vendor; Vexa's platform coverage and reliability should be validated early in Phase 5, since it's a smaller, newer project than Recall.ai |
| **WhatsApp template messages** | **Removed entirely** — Email (Brevo) is now the sole candidate messaging channel | Loses the WhatsApp channel the PRD originally called out for Indian candidate reach; documented as a deliberate scope cut (PRD §10), reversible later as an approved paid addition if data shows it's needed |

**Net effect:** every tool in §2 above is now ✅ or rate-limited-but-free (⚠️→✅ with graceful degradation) — there is no remaining line item that requires a card or a subscription for the development/pilot stage.

## 4a. STT Decision — Groq-Hosted Whisper, Not Self-Hosted (resolved 2026-07-20)

Originally an open question in this document: self-hosted Whisper (chosen alongside AI4Bharat when Sarvam AI was ruled out) carried a documented latency risk, since CPU-only inference was the only zero-cost hosting option and GPU is never free on any mainstream cloud. Your Groq dashboard showed `whisper-large-v3` and `whisper-large-v3-turbo` available on the free tier — genuinely free, LPU-accelerated, no self-hosting needed.

**Decision: switched to Groq-hosted Whisper.** Implemented as a two-model chain in `app/connectors/speech_to_text.py` — `whisper-large-v3-turbo` first (faster, better fit for the ~1s real-time target), `whisper-large-v3` second (marginally more accurate, separate quota bucket, so chaining ~doubles the daily audio budget to roughly 4,000 requests/day and 57,600 audio-seconds/day combined). Confirmed working end-to-end against a real key.

**In plain terms, the one trade-off this creates:** Groq is now doing two jobs for this project — backup LLM (when Gemini's free tier runs out) and speech-to-text. If Groq's own servers ever have an outage, **both jobs fail at the same time**, in the same live interview, because they depend on the same company's infrastructure being up. That's different from two unrelated services failing independently — it's one shared point of failure serving two purposes. There is currently no second STT provider configured to fall back to if this happens (`TranscriptionUnavailable`, distinct from `AIQuotaExhausted`); TRD §8 failure handling covers how the system should degrade (e.g., reschedule the interview) rather than crash.

This was judged an acceptable trade for $0 cost and materially lower latency risk than the self-hosted alternative, given Groq's free tier is independently already the fallback LLM provider in this design — not a new dependency, just an expanded role for an existing one.

## 4b. STT/TTS Decision, Revised — Chrome In-Browser Web Speech APIs (resolved 2026-07-20)

Superseding §4a within the same day: you pointed out that Chrome ships free, built-in `SpeechRecognition` (STT) and `speechSynthesis` (TTS) APIs, and asked to use both, keeping Zoom/Meet as the actual meeting platform. That's a genuine further simplification over the Groq-hosted-Whisper plan in §4a.

**The catch that shaped the implementation:** `SpeechRecognition`/`speechSynthesis` are JavaScript APIs that only run inside a live browser tab — they can't be called as a headless API the way Groq's Whisper endpoint can. That ruled out keeping Vexa (which hands you raw audio bytes via an API, not a browser tab you can run your own JS in) as the meeting-join mechanism. **Decision: replace Vexa with a custom, self-hosted Playwright/Chromium bot** that joins Zoom/Meet via their browser web-join URLs, and runs Chrome's own Web Speech APIs directly inside that tab as the primary STT/TTS path. The already-built Groq-hosted Whisper chain and self-hosted AI4Bharat TTS are **kept, not discarded** — demoted to fallbacks if Chrome's in-browser recognition/synthesis is unavailable or fails.

**What this changes, net of §4a:**
- Removes Vexa from the design (an existing third-party open-source project) in favor of a bot we build ourselves — more engineering effort, zero vendor/reliability dependency on Vexa specifically.
- Demotes Groq-hosted Whisper from primary to fallback, which **also demotes the correlated-outage risk** flagged in §4a (Groq no longer needs to be up for STT to work under normal conditions — only if Chrome's own recognition fails).
- Introduces a new, unvalidated risk in its place: this bot runs headless on a Linux VM, and Chrome's `speechSynthesis` voice availability/quality — especially for Hindi/Marathi — depends on what speech engines that OS has installed. Desktop Chrome usually has good voices; a bare Linux server often defaults to robotic ones (e.g., espeak-ng). **Not yet tested for this project** — this needs to happen early in Phase 5, since it directly determines whether the "TTS primary" claim above actually holds or whether AI4Bharat should really be primary instead.
- Introduces the largest new engineering item in the whole system: **virtual audio routing** (piping the meeting's incoming audio into the browser tab as its "microphone," and the tab's synthesized speech back out as the bot's own mic) via an OS-level loopback device. This is comparable in complexity to what Vexa/Recall.ai solve internally — we're now building that ourselves for $0 instead of using their product.

**Net cost effect: still $0.** Chrome's Web Speech APIs have no metering, no API key, and no account at all — this is, if anything, a further cost simplification. The real cost of this decision is engineering time, not currency.

## 5. Residual Risks Worth Tracking (not cost, but adjacent)

- **Virtual-audio-routing build risk (new, from §4b):** the custom Playwright bot needs OS-level audio loopback to connect meeting audio to Chrome's Web Speech APIs — this is unbuilt and unproven, and is now the single highest-uncertainty piece of the entire system. Treat it as the first thing to prototype in Phase 5, before anything else in that phase.
- **Chrome TTS voice-quality risk on headless Linux (new, from §4b):** unvalidated; AI4Bharat remains the documented fallback if this doesn't hold up.
- **Self-hosting/ops burden:** the custom Playwright bot and AI4Bharat (as fallback) still need deployment, monitoring, and update effort a managed SaaS would otherwise absorb — and the bot itself is now something the team maintains rather than a third-party project (Vexa), which is more ownership than before, not less. This shows up as engineering time (Implementation Plan §2), not a bill, but it's real and should be tracked.
- **Free-tier terms drift:** Every "free forever" claim in this document is a snapshot from July 2026. Vendors change these terms without much notice — SendGrid's free plan disappearing in 2025 is one example already baked into this project's history, and **Oracle cut its Always Free Ampere VM allocation from 4 OCPU/24GB to 2 OCPU/12GB in June 2026 with no public announcement**, discovered only when instances were downgraded or shut down. Treat the Oracle VM figures in this document as best-effort-accurate at write time, verify the actual allocation at signup, and re-check before each phase kickoff — this vendor specifically has shown it will change terms silently.
- **Quality/latency gap vs. the original commercial-vendor design:** documented per-item in §4. This is the actual cost of this revision — paid in capability, not currency. Track it explicitly during Phase 5/7 testing (Implementation Plan) so it's a measured trade-off, not an assumed one.

## 6. Maintenance Protocol

This document must stay current as the single source of truth for "what are we paying for and why." Whenever a new tool, API, library-with-a-paid-tier, or subscription is introduced anywhere in this project:

1. Add a row to the §2 inventory table **before** the change is merged — category, used-by, usage estimate, free-tier terms (verified, not assumed), and status symbol.
2. It does not get added if it has no viable free/self-hosted path at our pilot scale — find a free alternative first, or bring it back to the Owner as an explicit, approved exception to the zero-cost policy (as §4 records were, before being resolved).
3. Re-verify free-tier terms at the start of each new phase in [05-Implementation-Plan.md](./05-Implementation-Plan.md) — they drift.
