# Project Overview — AI Recruiter Agent

*Plain-language explainer. For the formal specs see [01-PRD](./01-PRD.md) through [07-Financial-Subscription-Tracking](./07-Financial-Subscription-Tracking.md).*

---

## The problem

A solo recruiter, a founder doing their own hiring, or a two-person talent team spends most of a hiring cycle on repetitive work: writing the job post, collecting applications, reading resumes, scheduling interviews, chasing no-shows, running first-round screens, and writing them up. By the time they get to the decisions that actually need human judgment, they've burned days on logistics.

There are applicant tracking systems for big companies, but they're heavy, built for multi-stakeholder teams, and priced accordingly. There's nothing that lets one person say *"I need three backend interns, remote, Python and SQL"* in plain English and have the busywork handled up to — but not including — the hire/reject call.

## The solution

A web app where the recruiter (the "Owner") describes a role conversationally, and an AI agent runs the pipeline:

1. **Requirement intake** — the Owner types the brief; the AI turns it into a structured requisition and asks one clarifying question if something important is missing.
2. **Form generation** — the AI drafts the candidate application form (resume upload, basic info, skill questions, a mandatory notice that AI is involved); the Owner reviews and approves it. Nothing goes live without that click.
3. **Distribution** — the form is posted where the Owner has real API access; everywhere else (LinkedIn, Naukri, Internshala — all gated) the AI prepares the exact text and the Owner posts it themselves.
4. **Response monitoring** — applications flow in; the AI deduplicates them and, once a threshold is hit (default 5), moves to outreach automatically.
5. **Interview invitations** — sent by email in the candidate's language (English, Hindi, or Marathi) with date, time, format, and etiquette notes.
6. **The live interview** — at the scheduled time the AI creates a video meeting, a bot joins it, discloses that it's an AI and that the session is recorded, then conducts a structured, resume-aware interview by voice.
7. **Scoring** — the AI produces a transcript and a multi-dimension scorecard.
8. **The human gate** — the Owner reviews every scorecard and makes the shortlist/reject/hold call. **The AI never finalizes a hiring decision.**

Two hard rules run through the whole design:
- **A human confirms anything externally visible** — form goes live, message sent outside an official API, final candidate decision.
- **Candidates are always told they're dealing with an AI** — in the form, in the invitation, and out loud at the start of the interview.

## Why it's built the way it is

**Zero recurring cost.** Every piece is on a genuine free tier or is open-source self-hosted — no subscription is needed to run this at pilot scale. Where a capability had no free option at production quality, the system degrades gracefully instead of spending money (see the LLM section below). The one accepted cost is engineering time for the self-hosted pieces. Full ledger: [07-Financial-Subscription-Tracking.md](./07-Financial-Subscription-Tracking.md).

**The AI never runs unsupervised where it matters.** The human-confirmation gates aren't just good practice — they line up with the EU AI Act (which classifies recruitment AI as high-risk) and India's DPDP Act.

## How it works — the moving parts

```
  Recruiter's browser (React SPA)
        │  login (Supabase Auth + mandatory TOTP MFA)
        │  REST calls with a bearer token
        ▼
  FastAPI backend (Python)
        │
        ├── LLM Router ──────► Gemini free tier → Groq free tier
        │   (one entry point;    (each a chain of models; pauses and emails
        │    every agent uses     the Owner when both are exhausted for the
        │    it, never a model     day, instead of ever calling a paid model)
        │    directly)
        │
        ├── Agents (our logic): Requirement Parser, Form Builder,
        │   [later: Distribution, Response Monitor, Notification,
        │    Meeting Orchestration, Interview, Scoring]
        │
        └── Connectors (wrap external services):
            Supabase · Brevo (email) · Zoom · Groq Whisper (STT fallback) ·
            [later: the meeting-bot pipeline]

  Supabase (managed Postgres + Auth + Storage + Realtime)
        - system of record; RLS as a second isolation layer
        - free tier; auto-pauses after ~7 days idle (a keep-alive guards this)

  Oracle Cloud Always Free VM  [Phase 5]
        - the custom Playwright/Chromium meeting bot + AI4Bharat TTS fallback
```

**The interview voice pipeline** (Phase 5, not built yet): a custom browser bot joins the Zoom/Meet call and uses Chrome's *built-in* speech recognition and speech synthesis — free, no API. Groq-hosted Whisper and self-hosted AI4Bharat TTS are kept as fallbacks. The one genuinely hard unbuilt piece is the audio routing that connects the meeting to the browser tab.

**The quota safety net** (the LLM Router): free AI tiers are rate-limited, not spend-limited. When every free model is used up for the day, the system pauses all AI work, emails the Owner once, and resumes automatically at the next reset — it never falls through to a paid model. This is why the project can promise $0/month honestly.

## Tech stack

| Layer | Choice | Note |
|---|---|---|
| Frontend | React + TypeScript + Vite + Tailwind v4 | Single SPA — Owner Console now, candidate pages later |
| Backend | FastAPI (Python, async) | Hosts the agent orchestration |
| Database / Auth / Storage / Realtime | Supabase (managed Postgres + pgvector) | One platform; free tier |
| Auth | Supabase Auth, email/password + **required TOTP MFA** | Decided via an [LLM-council review](./decisions/) — chosen as the *minimal* option (schema already wired for it) |
| LLM | Gemini free tier → Groq free tier, via an in-house router | Per-model chains; graceful pause on exhaustion. No paid model in the loop. |
| Resume parsing | Same LLM router + open-source PDF text extraction | No dedicated vendor |
| Email | Brevo (free tier, 300/day) — sole candidate channel | WhatsApp evaluated and cut (per-message cost) |
| Speech-to-text | Chrome's built-in Web Speech API (primary) · Groq Whisper (fallback) | Phase 5 |
| Text-to-speech | Chrome's built-in `speechSynthesis` (primary) · self-hosted AI4Bharat (fallback) | Phase 5 |
| Meeting creation | Zoom API (free Basic, ≤40 min) · Google Meet (fallback) | |
| Meeting bot | Custom Playwright/Chromium, self-hosted | Phase 5; replaces the paid Recall.ai/Vexa |
| Hosting | Vercel/Netlify (frontend) · Cloud Run/Render (backend) · Oracle Cloud Always Free VM (voice pipeline) | All free tier |
| CI/CD | GitHub Actions (free tier) | |

## Where the project is now

**In progress:** a [two-week Phase 5 voice spike](./spikes/phase5-voice-spike.md) — the
[whole-project LLM Council](./decisions/council-report-20260910-205930.html)'s "one thing to do
first." Runs out of implementation-plan order, before Phase 2, to prove or kill the live
AI-interview pipeline (now targeting a self-hosted LiveKit room instead of joining Zoom/Meet
directly) before building more of the pipeline on top of an unvalidated assumption. Scaffold
lives in `spikes/voice-interview-spike/`; go/no-go decides whether Phase 5 proceeds as planned
or the interview step becomes asynchronous recorded screening instead.


**Done:**
- All 5 foundation connectors (Supabase, LLM Router, Speech-to-Text, Email, Zoom), verified live.
- Database schema applied (17 tables, RLS, storage buckets, Realtime).
- **LLM Router** with per-provider model chains and the pause-and-notify quota guard.
- **Requirement Parser Agent** and **Form Builder Agent** — both verified end-to-end against real Gemini.
- **Owner Console** frontend: chat intake, form preview/approval, AI-status chip — verified in a real browser.
- **Owner authentication**: Supabase Auth + mandatory MFA, backend JWKS verification, `owner_id` resolution.
- 65 backend + 9 frontend tests passing.

**Remaining, per [05-Implementation-Plan.md](./05-Implementation-Plan.md):**

| Phase | What's left |
|---|---|
| 1 (finishing) | Persist requisitions/forms with `owner_id`; keep-alive cron vs Supabase auto-pause; a break-glass second Owner account |
| 2 | Distribution Agent (API + Owner-confirm manual) · Response Monitor Agent (dedup, threshold trigger, Realtime counter) |
| 3 | Notification Agent — multilingual email invitations, confirm/reschedule flow |
| 4 | Meeting Orchestration Agent — Zoom/Meet creation at the scheduled time, link dispatch |
| 5 (largest) | The live interview pipeline: the Playwright bot, virtual audio routing (highest-uncertainty item), Chrome Web Speech STT/TTS, the interview logic agent, the AI-disclosure step, multilingual/code-switching validation |
| 6 | Scoring Agent · the Owner's mandatory decision screen · audit logging across every action |
| 7 | One real pilot hiring cycle, with metrics — especially how often the free LLM tiers ran out |
| 8 | Hardening; revisit the WhatsApp/Sarvam/Recall.ai/Claude trade-offs if there's revenue to fund a small paid tier |

## Key risks being tracked

- **The virtual audio routing for the meeting bot** — unbuilt, unproven, the single highest-uncertainty piece. Phase 5 prototypes it first.
- **Chrome's TTS voice quality on a headless Linux server** for Hindi/Marathi — unvalidated; AI4Bharat is the fallback.
- **Free-tier LLM quota** running out during a busy pilot day — handled gracefully (pause + notify), but if it happens often, that's the signal to accept a small paid tier.
- **Speech accuracy on Hindi/Marathi code-switching** — weaker with free options than the purpose-built commercial one that was ruled out on cost; needs a dedicated test pass before real candidates.
- **Supabase free-tier auto-pause** taking the app down after a week idle — a keep-alive ping is the mitigation.
