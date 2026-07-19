# Financial & Subscription Tracking Document
## AI Recruiter Agent — Conversational Agentic Hiring Assistant

**Version:** 2.1 — added Oracle Cloud Always Free VM as the host for the voice/meeting-bot pipeline
**Date:** July 19, 2026
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
| **Oracle Cloud Always Free ARM VM** 🔁 | Persistent hosting for the voice/meeting-bot pipeline | Vexa (meeting bot) + Whisper (STT) + AI4Bharat (TTS), running together as one long-lived process per interview | 1 VM, one interview at a time at pilot scale | Permanent free ARM VM — **currently 2 OCPU/12GB RAM** (Oracle cut this from 4 OCPU/24GB in June 2026 with no announcement; verify actual allocation at signup) | No paid fallback needed at pilot scale; if concurrency or RAM needs grow, next step is a small paid VM, not Cloud Run/Render (wrong architecture for this workload) | ✅ (verify terms at signup — see residual risk in §5) |
| **Zoom API** | Instant meeting creation (primary) | Meeting Orchestration Agent | 1:1 bot+candidate calls, ≤30 min each | Free Basic account: unlimited 1:1 meetings, capped at 40 min/session | Only need paid Zoom if interview length is raised above 40 min — not planned | ✅ |
| **Google Meet API** | Fallback meeting creation | Meeting Orchestration Agent | Occasional fallback calls | Free with any Google account | N/A at this scale | ✅ |
| **Sentry** | Error monitoring | All backend/frontend error tracking | Low error volume | Developer tier: 5,000 errors/mo free | Paid tier if error volume scales | ✅ |
| **Grafana + Prometheus** | Metrics/monitoring | Backend observability | Self-hosted | Open source, free forever | N/A (only the compute it runs on has a cost, already covered above) | ✅ |
| **Brevo** 🔁 | Transactional email — now the **sole** candidate messaging channel | Notification Agent | Interview invites, confirmations, status updates; low hundreds/mo | 300 emails/day, permanently free | Paid tier beyond 300/day — very unlikely at pilot scale | ✅ |
| **Google Gemini API** 🔁 | Primary LLM | LLM Router (TRD §3.1a) — nearly every agent | Highest-volume dependency | Gemini 2.5 Flash: 250 req/day free; Gemini 2.5 Flash-Lite: 1,000 req/day free; resets 00:00 Pacific Time; free only while billing stays disabled on the project | Router automatically falls through to Groq (below) | ✅ (rate-limited, not cost-limited) |
| **Groq API** 🔁 | Fallback LLM | LLM Router (TRD §3.1a) — triggered when Gemini's daily quota is hit | Fallback volume only | Llama 3.1/3.3 models, 30 RPM, 500K tokens/day free, no card, no expiry | Router pauses all AI-dependent actions and notifies the Owner once (TRD §3.1a) — no fallthrough to a paid model | ✅ (rate-limited, not cost-limited) |
| **Vexa** 🔁 | Meeting bot join + audio stream | Meeting Bot / Live Interview Agent | 1 bot-hour per interview | Open source (Apache 2.0), self-hosted — no vendor account, no per-minute fee | N/A — runs on the Oracle Cloud VM above, no separate cost | ✅ |
| **OpenAI Whisper** 🔁 | STT | Meeting Bot / Live Interview Agent | Real-time audio, every interview minute | Open source, self-hosted, free; quantized "small" model (faster-whisper) for CPU performance | N/A — runs on the Oracle Cloud VM above | ✅ (quality/latency trade-off, see §4) |
| **AI4Bharat Indic Parler-TTS / IndicF5** 🔁 | TTS (Hindi/Marathi/English) | Meeting Bot / Live Interview Agent | Real-time audio, every interview minute | Open source, self-hosted, free | N/A — runs on the Oracle Cloud VM above | ✅ (quality trade-off, see §4) |
| **Claude (Anthropic API)** 🔁 removed | — | — | — | No ongoing free tier | Replaced entirely by the Gemini→Groq LLM Router | — |
| **Sarvam AI** 🔁 removed | — | — | — | No ongoing free tier | Replaced by self-hosted Whisper + AI4Bharat | — |
| **Recall.ai / MeetStream.ai** 🔁 removed | — | — | — | 5 free hours total, then per-minute billing | Replaced by self-hosted Vexa | — |
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
| **Claude (LLM)** | Replaced with a **Gemini-primary, Groq-fallback router** (§3 above); pauses gracefully rather than ever falling through to a paid model | Lower reasoning quality than Claude Sonnet for nuanced interview follow-ups/scoring justification; daily request caps may bind on a busy pilot day, causing a temporary pause |
| **Sarvam AI (STT/TTS)** | Replaced with **self-hosted open-source Whisper (STT, quantized "small" model) + AI4Bharat Indic Parler-TTS/IndicF5 (TTS)**, hosted on an **Oracle Cloud Always Free VM** (CPU-only — GPU is never free on any mainstream cloud) | Materially weaker Hindi/Marathi code-switching accuracy than the purpose-built commercial option; realistic latency is ~0.5–2s on CPU, not the ~1s ideal target in TRD §7 — must be measured in Phase 5 testing, not assumed |
| **Recall.ai / MeetStream.ai (meeting bot)** | Replaced with **self-hosted Vexa** (open source, Apache 2.0), on the same Oracle Cloud VM — an existing free/open-source project, not a from-scratch build | Self-hosting/ops responsibility shifts to the team instead of being handled by a managed vendor; Vexa's platform coverage and reliability should be validated early in Phase 5, since it's a smaller, newer project than Recall.ai |
| **WhatsApp template messages** | **Removed entirely** — Email (Brevo) is now the sole candidate messaging channel | Loses the WhatsApp channel the PRD originally called out for Indian candidate reach; documented as a deliberate scope cut (PRD §10), reversible later as an approved paid addition if data shows it's needed |

**Net effect:** every tool in §2 above is now ✅ or rate-limited-but-free (⚠️→✅ with graceful degradation) — there is no remaining line item that requires a card or a subscription for the development/pilot stage.

## 5. Residual Risks Worth Tracking (not cost, but adjacent)

- **Self-hosting/ops burden:** Vexa, Whisper, and AI4Bharat all need deployment, monitoring, and update effort a managed SaaS would otherwise absorb. This shows up as engineering time (Implementation Plan §2), not a bill, but it's real and should be tracked.
- **Free-tier terms drift:** Every "free forever" claim in this document is a snapshot from July 2026. Vendors change these terms without much notice — SendGrid's free plan disappearing in 2025 is one example already baked into this project's history, and **Oracle cut its Always Free Ampere VM allocation from 4 OCPU/24GB to 2 OCPU/12GB in June 2026 with no public announcement**, discovered only when instances were downgraded or shut down. Treat the Oracle VM figures in this document as best-effort-accurate at write time, verify the actual allocation at signup, and re-check before each phase kickoff — this vendor specifically has shown it will change terms silently.
- **Quality/latency gap vs. the original commercial-vendor design:** documented per-item in §4. This is the actual cost of this revision — paid in capability, not currency. Track it explicitly during Phase 5/7 testing (Implementation Plan) so it's a measured trade-off, not an assumed one.

## 6. Maintenance Protocol

This document must stay current as the single source of truth for "what are we paying for and why." Whenever a new tool, API, library-with-a-paid-tier, or subscription is introduced anywhere in this project:

1. Add a row to the §2 inventory table **before** the change is merged — category, used-by, usage estimate, free-tier terms (verified, not assumed), and status symbol.
2. It does not get added if it has no viable free/self-hosted path at our pilot scale — find a free alternative first, or bring it back to the Owner as an explicit, approved exception to the zero-cost policy (as §4 records were, before being resolved).
3. Re-verify free-tier terms at the start of each new phase in [05-Implementation-Plan.md](./05-Implementation-Plan.md) — they drift.
