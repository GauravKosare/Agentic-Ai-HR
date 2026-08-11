# Technical Requirements Document (TRD)
## AI Recruiter Agent — Conversational Agentic Hiring Assistant

**Version:** 3.0 (Revised for zero-cost stack: Gemini/Groq free-tier LLM router, self-hosted speech, self-hosted meeting bot, Email-only)
**Date:** July 19, 2026

---

## 1. System Overview

Delivered as a **web application** — a React/TypeScript frontend (Owner Console + candidate-facing pages) served over the browser, backed by a FastAPI service running the orchestration logic, with **Supabase** as the unified backend platform (Postgres + pgvector, Auth, Storage, Realtime). A single orchestrated AI agent manages the full pipeline from natural-language requirement intake through live interview conduction, calling out to specialized sub-services (form generation, platform posting, messaging, meeting creation, meeting-bot interviewing, multilingual speech) at each stage. A lightweight web dashboard gives the Owner visibility and control (approve form, confirm decisions); no native/desktop app is required for either the Owner or the candidate.

**Cost policy:** every component in this document is chosen to run on a genuinely free tier or free/open-source self-hosted software for the development/pilot stage — no subscription or per-use fee is required to build and run this system at pilot scale. See [07-Financial-Subscription-Tracking.md](./07-Financial-Subscription-Tracking.md) for the full, continuously-verified breakdown. The one deliberate exception is that free API tiers are *rate-limited*, not unlimited — §3.1a describes how the system degrades gracefully rather than incurring cost when a limit is hit.

## 2. High-Level Architecture

```
                     ┌───────────────────────────────┐
                     │  Owner (Recruiter) Web Console   │
                     │  React SPA — Chat/Form/Review UI │
                     │  Auth: Supabase Auth             │
                     └───────────────┬───────────────┘
                                     │  (REST/WebSocket)
                     ┌───────────────▼───────────────┐
                     │   Orchestrator Agent (LangGraph  │
                     │   FSM, FastAPI backend)          │
                     │   → LLM Router (§3.1a):           │
                     │     Gemini API (free tier) first, │
                     │     Groq API (free tier) fallback │
                     └───────────────┬───────────────┘
                                     │
                     ┌───────────────▼───────────────┐
                     │   Supabase (Postgres+pgvector,   │
                     │   Auth, Storage, Realtime)        │
                     └───────────────────────────────┘
        ┌───────────────┬────────────┼────────────┬───────────────┐
        ▼               ▼            ▼            ▼               ▼
   Requirement      Form Builder   Distribution  Response      Notification
   Parser Agent      Agent         Agent         Monitor       Agent
        │               │            │            │               │
        ▼               ▼            ▼            ▼               ▼
   Structured      Dynamic Form   Platform APIs / Postgres    Email only
   Requisition      (React/JSON)   Owner-confirm  (candidates,  (Brevo,
   (Postgres)       Schema         posting        responses)    free tier)

                     ┌───────────────────────────────┐
                     │   Meeting Orchestration Agent    │
                     └───────────────┬───────────────┘
        ┌───────────────┬────────────┼────────────┬───────────────┐
        ▼               ▼            ▼            ▼               ▼
   Zoom API         Google Meet   Custom Chrome    In-Browser      Scoring
   (instant          API           Bot (Playwright, Speech (Chrome  Agent
   meeting,          (fallback)    self-hosted,     SpeechRecog +   (LLM
   primary,                        joins via web     speechSynthesis, Router)
   free 1:1)                       client, $0)       fallback: Groq
                                                       STT/AI4Bharat TTS)
                                         │
                                         ▼
                                  Interview Transcript
                                  + Scorecard → Dashboard
                                  → Owner Confirms Decision
```
*The Playwright/Chromium bot (and its AI4Bharat TTS fallback) run together on one persistent Oracle Cloud Always Free VM — see §3.7 and §4 (Hosting). Chrome's `SpeechRecognition`/`speechSynthesis` run inside that same browser process; the Groq STT fallback is an API call, not hosted on the VM.*

## 3. Core Components

### 3.1 Requirement Parser Agent
- Takes the Owner's natural-language brief (chat message or short form) and extracts structured fields: role title, quantity, work mode (onsite/remote/hybrid), duration, compensation/stipend, required skills, eligibility criteria, seniority level.
- Model: routed through the **LLM Router** (§3.1a) — Gemini free tier primary, Groq free tier fallback.
- Output validated against a JSON schema before proceeding; ambiguous fields trigger a single clarifying question back to the Owner (not silent assumption).

### 3.1a LLM Router / Quota Manager — the zero-cost LLM layer
Every LLM call in the system (requirement parsing, form generation, resume parsing, interview dialogue, scoring) goes through one router instead of calling a model directly:

1. **Primary: Google Gemini API, free tier — per-tier model CHAIN, not a single model.** Each tier (reasoning / light) has an ordered list of models; a quota (`429`) error on one model moves to the *next model in the same chain* before ever switching provider, since Gemini's free daily quota is per-model, not per-account. As of 2026-07-20: reasoning tries `gemini-3.5-flash` then `gemini-3-flash` (each carries its own small daily quota — chaining roughly doubles the daily reasoning budget); light tries `gemini-3.1-flash-lite` then Google's open-weight `gemma-4-26b`/`gemma-4-31b` served through the same API, which carry a much larger daily allowance and act as a large free reserve before Groq is ever touched. Free tier is enforced by Google as long as billing is not enabled on the project — do not enable billing, or the free tier disappears. *(Model names and per-model quotas last verified against a live account 2026-07-20 — Gemini 2.0 was shut down 2026-06-01 and 2.5 Flash-Lite is no longer offered to new users, and free-tier limits are account-specific and drift; re-check yours in Google AI Studio rather than trusting this document, see [src/backend/app/core/config.py](../src/backend/app/core/config.py).)*
2. **Fallback: Groq API, free tier — also a per-tier chain.** Once every model in Gemini's chain for that tier is quota-exhausted, the router walks Groq's chain for the same tier the same way. As of 2026-07-20: reasoning tries `openai/gpt-oss-120b` then `llama-3.3-70b-versatile` then `qwen/qwen3.6-27b` (each with its own ~1K/day quota, verified from Groq's live rate-limits console); light tries `openai/gpt-oss-20b` then `llama-3.1-8b-instant`, which carries a far larger free daily allowance than every other model in either chain and is deliberately saved for last as the deep reserve. Groq's free tier requires no card and does not expire. *(Model lineups and rate limits change — Groq flagged `llama-3.3-70b-versatile`/`llama-3.1-8b-instant` for migration on 2026-06-17 but both were still live with published quotas as of this verification; re-check console.groq.com/docs/rate-limits before relying on this document.)*
3. **Task-specific routing.** Each named agent below (Requirement Parser, Form Builder, resume parsing, Response Monitor's dedup/classification step, Meeting Bot interview dialogue, Scoring Agent) maps to exactly one tier — reasoning or light — enforced in one place in the router, not decided ad hoc per call site. See `TASK_TIER` in the code linked above.
4. **Exhaustion — pause, don't spend.** Only once *every model in both providers' chains* for that tier has returned quota-exceeded does the router stop — it does **not** fall through to any paid model. Instead it:
   - Sets a system-wide `ai_paused` flag (with a `resume_at` timestamp — Gemini's daily quota resets at 00:00 Pacific Time; Groq's free-tier reset timing must be re-verified against current docs before relying on it, see [07-Financial-Subscription-Tracking.md](./07-Financial-Subscription-Tracking.md)).
   - Sends the Owner **one** notification (Email) — a "last reminder" summarizing what ran out (Gemini and/or Groq), how many requests/tokens were used today, and when the system will resume automatically.
   - Halts every AI-dependent action (parsing, form drafting, interview dialogue, scoring) until the quota window resets, at which point the router clears `ai_paused` and resumes automatically — no manual restart needed.
   - Actions that don't need the LLM (viewing the dashboard, manually posting a form, Owner confirming a decision) continue to work normally while paused.
- This event is logged to `audit_log` (`action = 'ai_quota_paused'` / `'ai_quota_resumed'`, see [06-Backend-Schema.md](./06-Backend-Schema.md)) so quota-exhaustion frequency is visible over time — if it happens often, that's the signal to reconsider the "accept a small paid tier" trade-off, not a silent failure mode.

### 3.2 Form Builder Agent
- Generates a candidate-facing application form (fields matched to requisition: resume upload, basic info, skill self-assessment, availability, language preference).
- Rendered as a hosted web form — a route within the same React web application, not a separate product — or via a form-service API (e.g., Typeform API) for faster time-to-market.
- Resume file uploads go directly to a **Supabase Storage** bucket (`resumes`, private, signed-URL access only); the stored `file_url` in Postgres is a Storage object path.
- Owner reviews/edits in a preview screen before the form goes live — **one-click approve, not silent auto-publish**.

### 3.3 Distribution Agent
- Posts the approved form/listing to connected platforms.
- **Verified access reality (July 2026):**
  - LinkedIn Talent Solutions API: partner-gated, 3–6 month approval, <10% approval rate; new "Apply with LinkedIn" partnerships closed since Oct 1, 2025.
  - Internshala: no confirmed public employer API — treat as manual/portal posting.
  - Naukri: enterprise-contract-gated recruiter API.
- **Design accordingly:** where official API access exists, post directly; otherwise the agent prepares the exact listing content and hands the Owner a single-click "Post now" action inside their own logged-in platform session (Owner-in-the-loop, not silent bot automation of a third-party UI).

### 3.4 Response Monitor Agent
- Polls/receives webhooks for new applications per requisition.
- Deduplicates by email/phone hash.
- Maintains a live count per requisition; fires an event once the configurable threshold (**default: 5**) is met.
- The Owner Console's response-counter and pipeline views subscribe to **Supabase Realtime** (Postgres logical replication over WebSocket) on the `applications` table, so the web UI updates live without polling.

### 3.5 Notification Agent (Email-only)
- **Email, via Brevo** (permanent free tier, 300/day), is the sole candidate communication channel — interview invitations, confirmations, reminders, and status updates.
- **WhatsApp has been removed from the design.** It was previously dual-channel with Email, but Meta bills business-initiated template messages (exactly what an interview invite is) per message with no free path around it — that's a real per-message cost with no zero-cost alternative, so it doesn't meet this project's cost policy. See [07-Financial-Subscription-Tracking.md §4](./07-Financial-Subscription-Tracking.md) for the decision record. If candidate reach via WhatsApp becomes a business priority later, it can be re-added as an explicit, approved paid line item — it is not a silent gap, it's a deliberate scope cut.
- Messages include interview date, time, format, duration/time limit, and a plain-language etiquette/protocol note (camera on, quiet environment, ID verification, etc.), delivered in the candidate's selected language.

### 3.6 Meeting Orchestration Agent
- At the scheduled time, creates an **instant Zoom meeting** via the Zoom API (primary) or a Google Meet link (secondary/fallback where the candidate prefers Meet).
- **Free-tier constraint:** a Zoom Basic (free) account is capped at 40 minutes per meeting, including 1:1 calls. Interviews must stay at or under this — the system already defaults `interview_time_limit_minutes` to 30 (see [06-Backend-Schema.md](./06-Backend-Schema.md)), which fits comfortably. If the Owner ever raises the default above 40 minutes, this becomes a paid-Zoom-account requirement and must be flagged.
- Sends the join link via Email shortly before the scheduled time.

### 3.7 Meeting Bot / Live Interview Agent — Browser-Native Design (revised 2026-07-20)
- **Meeting join is now a custom, self-hosted Chrome bot, not Vexa.** A **Playwright-driven Chromium browser** joins the Zoom/Meet call via each platform's browser-based web-join URL (no native app install, no host permission needed) — this replaces Vexa entirely. The reason: Chrome's Web Speech APIs (`SpeechRecognition`, `speechSynthesis`) only run inside a live browser page, not as a headless audio-processing service, so the bot needs to actually *be* a browser tab we control rather than a service that just hands us raw audio bytes (which is what Vexa provided).
- **STT primary: Chrome's built-in `SpeechRecognition`**, running inside that browser tab — free, no API key, no per-minute cost. **STT fallback:** the already-built Groq-hosted Whisper chain (`whisper-large-v3-turbo` → `whisper-large-v3`, `app/connectors/speech_to_text.py`, kept rather than discarded) if in-browser recognition is unavailable or fails.
- **TTS primary: Chrome's built-in `speechSynthesis`**, same tab, same reasoning — free, and typically lower-latency than a network round-trip to a hosted model since synthesis happens locally in the browser process. **Open risk, not yet validated:** this bot runs headless on a Linux VM (Oracle Cloud, §4), and Chrome's available `speechSynthesis` voices — especially quality Hindi/Marathi voices — depend entirely on what speech engines are installed on that OS. Desktop Chrome (Windows/macOS) typically has good voices available; a bare Linux server often only has robotic default voices (e.g., espeak-ng) unless better ones are installed. **This must be tested early in Phase 5** ([05-Implementation-Plan.md](./05-Implementation-Plan.md)) before committing to it for real candidates. Self-hosted **AI4Bharat Indic Parler-TTS/IndicF5** remains documented as the fallback/mitigation if Chrome's Linux voice quality proves unacceptable — not deleted from the design, demoted to contingency.
- Real-time pipeline: candidate speech (arrives via the meeting's WebRTC audio) → routed into the bot's browser tab as its "microphone" input → **Chrome `SpeechRecognition`** (STT) → transcribed text → **LLM Router** (§3.1a — question generation/adaptive follow-up, grounded in resume + prior answers) → **Chrome `speechSynthesis`** (TTS) → routed back out as the bot's own "microphone" audio into the meeting.
- **The genuinely new engineering piece: virtual audio routing.** Getting the meeting's incoming audio into `SpeechRecognition` and the bot's synthesized speech back out as its own mic input requires an OS-level virtual audio loopback (e.g., a Linux `pulseaudio`/`pipewire` loopback device) connecting the browser tab's audio in/out to the WebRTC call. This is comparable in complexity to what Vexa/Recall.ai solve internally — the difference is we're building it ourselves for $0 instead of paying a vendor or depending on Vexa's smaller/newer open-source project. Budget real time for this in Phase 5; it is the highest-uncertainty piece of the whole system.
- **Honest capability trade-off vs. the original Sarvam AI design:** unchanged in kind from the prior Whisper-based plan — Chrome's `SpeechRecognition` (which is itself cloud-processed by Google under the hood, not on-device) is expected to be weaker on Hindi/Marathi code-switching than a purpose-built commercial model, and its accuracy on Indian languages specifically has not been benchmarked for this project. Budget dedicated multilingual/code-switching test time in Phase 5 to quantify the real gap, same as the Whisper-based plan required — this decision doesn't remove that risk, it changes which free option carries it.
- **Latency:** likely a net improvement over the Groq/AI4Bharat design — both `SpeechRecognition` and `speechSynthesis` avoid a network round-trip to an external inference API, since Chrome handles them directly. Not yet measured for this project; validate in Phase 5 against the ~1s target in §7.
- **Hosting fit unchanged:** the Playwright/Chromium bot (plus AI4Bharat as TTS fallback) still needs a **persistent VM** (§4, Hosting — Oracle Cloud Always Free tier), not a serverless platform — a live meeting-audio session is a long-running stateful process, architecturally a poor fit for Cloud Run/Render.
- Follows a standard interview protocol: opening/rapport → resume-specific questions → role-relevant technical/behavioral questions → adaptive follow-ups → closing.
- Candidate is informed at meeting start (spoken + earlier written notice) that the interviewer is AI and the session is recorded.

### 3.8 Scoring Agent
- Generates a multi-dimension scorecard (communication, technical depth, problem-solving, role fit) with justification text, using the **LLM Router** (§3.1a) against the transcript.
- Full transcript + audio/video retained per data retention policy.

### 3.9 Human Decision Gate
- Owner Dashboard surfaces every scorecard + transcript.
- Owner must actively confirm shortlist/reject — no status is ever finalized without this action.
- Any override of AI's implied recommendation requires a short justification note (logged for audit).

### 3.10 Audit & Compliance Layer
- Every automated action (form generated, posted, message sent, meeting created, score generated, AI paused/resumed on quota exhaustion) logged immutably: `entity, action, actor(system/user), timestamp, details`.
- Consent status tracked per candidate per channel (data processing, email, AI interview).

## 4. Tech Stack (Updated & Verified — zero-cost stack)

| Layer | Technology |
|---|---|
| Application shape | **Web application** — single React SPA serving both the Owner Console and candidate-facing pages (application form, invite confirmation, outcome), no native app |
| Orchestration | LangGraph (Python) or custom FSM |
| LLM | **Gemini API (free tier)** primary, **Groq API (free tier)** fallback, routed through the LLM Router (§3.1a) — requirement parsing, form generation, resume parsing, interview dialogue, scoring. No paid model in the loop; the router pauses rather than spending when both free tiers are exhausted for the day. |
| Resume Parsing | Same **LLM Router** (structured-extraction prompt against resume text) + open-source **PyMuPDF/pdfplumber** for local PDF→text extraction — no dedicated resume-parsing vendor |
| Form Hosting | Route within the same React web app (primary) or Typeform API embed (faster time-to-market fallback) |
| Backend Platform | **Supabase** — Postgres (with `pgvector`) as primary DB, Supabase Auth, Supabase Storage, Supabase Realtime (see §5.1) |
| Primary DB | **Supabase Postgres** (managed, with `pgvector` extension enabled) |
| Vector DB (resume/JD matching) | `pgvector` extension on Supabase Postgres — no separate vector DB needed at MVP scale |
| File Storage (resumes, recordings) | **Supabase Storage** — private buckets, signed-URL access |
| Realtime updates (response counter, pipeline status) | **Supabase Realtime** — Postgres change subscriptions over WebSocket to the Owner Console |
| Email | **Brevo** (permanent free tier, 300 emails/day) — sole candidate messaging channel |
| Video Meeting Creation | Zoom API (primary, free Basic account — 40 min cap on 1:1 calls, comfortably above our 30-min default); Google Meet API (secondary/fallback, free with any Google account) |
| Meeting Bot (AI joins call) | **Custom Playwright/Chromium bot**, self-hosted — joins Zoom/Meet via each platform's web-join URL. Replaces Vexa (§3.7): needed because Chrome's Web Speech APIs only work inside a live browser tab we control, not via a headless audio-stream service. |
| Speech (STT) | **Chrome's built-in `SpeechRecognition`**, running inside the bot's browser tab — free, no API key. Fallback: **Groq-hosted Whisper** (`whisper-large-v3-turbo` → `whisper-large-v3` chain, kept from the prior design, `app/connectors/speech_to_text.py`). |
| Speech (TTS) | **Chrome's built-in `speechSynthesis`**, same tab — free, likely lower latency (no network round-trip). **Unvalidated risk:** headless-Linux voice quality/availability for Hindi/Marathi, test in Phase 5. Fallback: **self-hosted AI4Bharat Indic Parler-TTS / IndicF5**. |
| Backend API | FastAPI (Python) — hosts the orchestrator, calls Supabase via service-role key for privileged operations |
| Frontend (Owner Console + candidate pages) | React + TypeScript, Tailwind — talks to Supabase directly (Auth, Realtime, Storage) for client-safe operations, and to the FastAPI backend for agent/orchestration actions |
| Auth | **Supabase Auth** (email/password + OAuth providers) for the single-Owner MVP; candidate-facing pages remain unauthenticated/token-link based |
| Hosting | Frontend: Vercel or Netlify (free tier). Backend API (FastAPI/LangGraph — requirement parsing, form, distribution, notifications, scoring): **Google Cloud Run free tier** (2M requests/mo) or Render free Web Service (cold-start tolerant, fine for these stateless request/response paths). **Voice/meeting-bot pipeline (Vexa + Whisper + AI4Bharat, §3.7):** an **Oracle Cloud Always Free ARM VM** (currently 2 OCPU / 12GB RAM, permanent — not a trial), not Cloud Run/Render — this is a long-running, stateful process for the duration of each interview, which doesn't fit a serverless request/response model; a persistent VM is the correct architectural fit and Oracle's Always Free tier is the only mainstream option that's a genuine permanent free VM rather than a time-boxed trial. Database/Auth/Storage: Supabase-managed (free tier). |
| Monitoring | Grafana + Prometheus (self-hosted, free), Sentry (free developer tier), plus Supabase's built-in project logs/metrics |
| CI/CD | GitHub Actions (free tier) |

Full free-tier terms, usage tracking, and the decision record for every swap above live in **[07-Financial-Subscription-Tracking.md](./07-Financial-Subscription-Tracking.md)** — treat it as the source of truth, not this table.

## 5. Integration Points — Verified July 2026

| Integration | Purpose | Access Reality |
|---|---|---|
| **Supabase** | Postgres DB + pgvector, Auth, Storage, Realtime | Self-serve, generous free tier, managed Postgres |
| LinkedIn Talent Solutions API | Post jobs, pull applicants | Gated, slow, AWLI closed to new partners since Oct 2025 — treat as Owner-manual for MVP |
| Internshala | Post internships | No confirmed public API — Owner-manual/CSV for MVP |
| Naukri Recruiter API | Post jobs | Enterprise-contract-gated — Owner-manual for MVP |
| Brevo | Email (sole candidate channel) | Self-serve, permanent free tier (300/day) |
| Zoom API | Instant meeting creation | Self-serve developer API; free Basic account sufficient (40-min/1:1 cap, we default to 30 min) |
| Google Meet API | Fallback meeting creation | Self-serve, free with any Google account |
| Gemini API | Primary LLM (free tier) | Self-serve via Google AI Studio; free while billing is disabled on the project |
| Groq API | Fallback LLM (free tier) | Self-serve, no card required, no expiry |
| Playwright (Chromium automation) | Custom meeting-bot join (replaces Vexa) | Open source (Apache License 2.0), self-hosted — no vendor account/billing |
| Chrome `SpeechRecognition` / `speechSynthesis` | STT/TTS primary, in-browser | Built into Chromium, no API key, no vendor account — see TRD §3.7 for the headless-Linux voice-quality risk to validate |
| Groq (Whisper STT) | STT fallback — `whisper-large-v3-turbo` → `whisper-large-v3` chain | Self-serve, free tier, LPU-accelerated hosted API; same GROQ_API_KEY as the LLM Router fallback |
| AI4Bharat Indic Parler-TTS / IndicF5 | TTS fallback (Hindi/Marathi/English) | Self-hosted, free — run on own compute |
| **Oracle Cloud Always Free tier** | Persistent VM hosting the Playwright/Chromium bot + AI4Bharat TTS fallback | Self-serve, permanent free ARM VM (currently 2 OCPU/12GB RAM — Oracle cut this from 4 OCPU/24GB in June 2026 with no announcement; verify current allocation at signup and re-check periodically, see [07-Financial-Subscription-Tracking.md](./07-Financial-Subscription-Tracking.md)) |

### 5.1 Supabase Usage Detail

- **Auth:** Owner login/session management via Supabase Auth (email/password at MVP; OAuth providers can be added without a schema change). The `owners` table carries a foreign key to `auth.users`.
- **Database:** Supabase-managed Postgres is the system of record for every table in [06-Backend-Schema.md](./06-Backend-Schema.md); `pgvector` runs as a Postgres extension on the same instance — no separate vector database.
- **Row Level Security (RLS):** Enabled on every table containing Owner or candidate data, scoped so an authenticated Owner can only read/write rows tied to their own `owner_id`. The FastAPI backend uses the Supabase **service-role key** (bypasses RLS) for orchestration writes (e.g., agent-generated records); the frontend uses the **anon/public key** plus RLS for any direct client reads.
- **Storage:** Two private buckets — `resumes` (candidate resume files) and `recordings` (interview audio/video) — both signed-URL access only, never public.
- **Realtime:** Postgres change-data-capture subscriptions power live UI updates (response counter, pipeline status) without the frontend polling the backend.

## 6. Data Flow Summary

1. Owner states requirement (chat/form) → Requirement Parser Agent (via LLM Router) → structured requisition stored in Supabase Postgres.
2. Form Builder Agent generates form → Owner approves → Distribution Agent posts (API where possible, Owner-confirmed manual otherwise).
3. Response Monitor Agent tracks applications → fires event at ≥5 responses; Owner Console reflects the live count via Supabase Realtime.
4. Notification Agent sends interview invite via Email (candidate's language) with date/time/format/protocol.
5. Candidate confirms → Meeting Orchestration Agent creates Zoom/Meet instant meeting at scheduled time (≤40 min, free-tier constraint) → sends join link.
6. Custom Playwright/Chromium bot joins the meeting → real-time STT (Chrome `SpeechRecognition`, fallback Groq-hosted Whisper) → LLM Router interview logic → real-time TTS (Chrome `speechSynthesis`, fallback self-hosted AI4Bharat) → live conversation; recording lands in Supabase Storage.
7. Scoring Agent (via LLM Router) generates scorecard from transcript → surfaced on Owner Console (web app).
8. Owner reviews and confirms final decision → status updated in Supabase → candidate notified via Email.

*If the LLM Router's free tiers are both exhausted at any point in steps 1, 2, 6, or 7, the pipeline pauses at that step (§3.1a) and resumes automatically at the next quota reset — no cost is incurred, and the Owner is notified once.*

## 7. Performance Requirements

- Requirement-to-form-draft: under 2 minutes of processing time (assuming the LLM Router is not in a paused state).
- Real-time interview STT→LLM→TTS round trip: target under ~1 second for natural conversational pacing. Chrome's in-browser `SpeechRecognition`/`speechSynthesis` avoid a network round-trip and are expected to help here, but this is unmeasured for this project — benchmark on the actual Oracle Cloud Always Free VM in Phase 5 (§3.7, §4) before treating the ~1s figure as guaranteed. If either fallback path (Groq STT / AI4Bharat TTS) is engaged, expect the previously-documented 0.5–2s range instead.
- Email dispatch after threshold trigger: under 5 minutes.
- Meeting bot join time after meeting creation: under 30 seconds.

## 8. Failure Handling

- If the meeting bot (custom Playwright/Chromium) fails to join: auto-retry twice, then notify Owner and auto-reschedule candidate with an apology message.
- If Chrome's in-browser `SpeechRecognition`/`speechSynthesis` is unavailable or fails mid-interview: fall back to Groq-hosted Whisper (STT) / self-hosted AI4Bharat (TTS) respectively for the remainder of that session, logged for later review.
- If the LLM Router's free tiers are both exhausted (§3.1a): system pauses all AI-dependent actions, sends the Owner one reminder notification, and resumes automatically at the next quota reset — this is expected behavior under the zero-cost policy, not an error state, but repeated occurrences should prompt a review of whether to accept a small paid tier.
- If Email delivery fails (e.g., invalid address, Brevo daily cap reached): flag for Owner review; retry once after a delay.
- If platform posting API call fails: retry with backoff; if persistent, surface to Owner as a manual-action item.
