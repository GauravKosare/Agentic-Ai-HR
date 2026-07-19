# Implementation Plan
## AI Recruiter Agent — Conversational Agentic Hiring Assistant

**Version:** 3.0 (Revised for zero-cost stack: Gemini/Groq LLM router, self-hosted speech/meeting bot, Email-only)
**Date:** July 19, 2026

---

## 1. Phased Roadmap

### Phase 0: Foundation & Account Setup (Weeks 1–2)
- Provision the **Supabase** project: Postgres database (schema from [06-Backend-Schema.md](./06-Backend-Schema.md)), enable `pgvector`, configure Auth (email/password), create private Storage buckets (`resumes`, `recordings`), enable Realtime on the `applications` table, write initial RLS policies.
- Scaffold the React web app (Owner Console shell) and connect it to Supabase Auth for login/session.
- Scaffold the FastAPI backend and connect it to Supabase via the service-role key.
- Set up the **LLM Router** (TRD §3.1a): Gemini API key (free tier, billing left disabled) + Groq API key (free tier), with fallback and quota-pause logic wired in from day one — every later phase depends on this, not on any paid model.
- Connect core external services: Brevo (email, permanent free tier), Zoom API, Google Meet API — no WhatsApp/BSP setup (removed from scope, see [07-Financial-Subscription-Tracking.md](./07-Financial-Subscription-Tracking.md)).
- Provision the **Oracle Cloud Always Free ARM VM** (currently 2 OCPU/12GB RAM) that will host the Vexa + Whisper + AI4Bharat pipeline in Phase 5 — set it up early so the team has a stable target environment, even though nothing runs on it until Phase 5. Confirm the current free allocation at signup (Oracle changed these terms without notice in June 2026) and document it in [07-Financial-Subscription-Tracking.md](./07-Financial-Subscription-Tracking.md).
- Legal/compliance review of consent flows (DPDP-aligned notice/consent, email opt-in).

**Deliverables:** Owner can sign up/log in via the web app (Supabase Auth); RLS confirmed to isolate one Owner's data from another's; a test call succeeds through the LLM Router (Gemini path); a forced-quota test confirms the Groq fallback and pause-with-notification behavior both work; email test message sends successfully via Brevo; Zoom instant meeting can be created via API test call.

### Phase 1: Requirement Intake & Form Generation (Weeks 3–5)
- Build Requirement Parser Agent (via the LLM Router) — natural language → structured requisition.
- Build Form Builder Agent — requisition → dynamic candidate form.
- Owner Console: chat intake screen + form preview/approval screen, including the AI-status indicator (TRD §3.1a / UI/UX §4.3a).

**Deliverables:** Owner can describe a role in chat and get an approvable form within minutes; UI correctly shows "AI paused" if triggered during testing, and resumes automatically without developer intervention.

### Phase 2: Distribution & Response Monitoring (Weeks 5–8) *(overlaps Phase 1)*
- Build Distribution Agent — direct API posting where available (evaluate current partner status for each target platform); Owner-confirm manual flow for LinkedIn/Naukri/Internshala given current access constraints.
- Build Response Monitor Agent — polling/webhook ingestion, dedup, live counter, threshold trigger (default 5).
- Build resume parsing: open-source PyMuPDF/pdfplumber (PDF→text) feeding a structured-extraction prompt through the LLM Router — no dedicated resume-parsing vendor.

**Deliverables:** A form posted (via API or Owner-confirmed manual action) with responses flowing into the Pipeline view, resumes parsed into structured fields at $0 marginal cost, and the pipeline triggering the next stage automatically at threshold.

### Phase 3: Multilingual Email Notification (Weeks 8–10)
- Build Notification Agent: Email templates via Brevo — no WhatsApp template submission/approval step, which simplifies this phase versus the original plan.
- Language preference capture on the candidate form; translated template content for English/Hindi/Marathi.
- Interview invite content: date, time, format, time limit, etiquette note.

**Deliverables:** Candidate receives a correctly localized interview invite via Email upon threshold trigger, with working confirm/reschedule actions.

### Phase 4: Meeting Automation (Weeks 10–12)
- Build Meeting Orchestration Agent — Zoom instant meeting creation at scheduled time (primary, free Basic account, ≤40 min), Google Meet fallback.
- Join-link dispatch via Email shortly before start time.

**Deliverables:** At a scheduled time, a real Zoom meeting is auto-created within the free-tier time limit and the link delivered to a test candidate account via Email.

### Phase 5: Live AI Interview Pipeline (Weeks 12–20) — Highest-Complexity Phase, Extended
- Deploy **Vexa** (open source, self-hosted), **Whisper** (STT, quantized "small" model via faster-whisper for CPU performance), and **AI4Bharat Indic Parler-TTS/IndicF5** (TTS) together on the **Oracle Cloud Always Free VM** provisioned in Phase 0 — a persistent process, not a serverless deployment (TRD §3.7, §4).
- Build interview logic agent (via the LLM Router): resume-grounded question generation, adaptive follow-ups, standard protocol (opening → resume Qs → role Qs → adaptive follow-ups → closing).
- Build disclosure step (spoken + written) confirming AI interviewer + recording consent at meeting start.
- **New vs. the original plan:** dedicate explicit test time to quantifying the code-switching accuracy gap between self-hosted Whisper/AI4Bharat and the originally-specified commercial option (TRD §3.7) — this is why this phase is now 8 weeks instead of 6. Also measure real STT→LLM→TTS latency on the actual Oracle VM (expect 0.5–2s on CPU, per TRD §7) rather than assuming the ~1s target is met.
- Extensive internal testing across all three languages and common code-switching patterns before any real candidate use.

**Deliverables:** A functioning end-to-end AI-conducted interview in a test meeting, in each of English, Hindi, and Marathi, running entirely on the Oracle Cloud Always Free VM with $0 API/hosting spend; measured (not assumed) latency and code-switching accuracy numbers, with a documented decision on whether they're acceptable for real candidates or need a fallback (e.g., English-only, or a human-conducted interview) for a given session.

### Phase 6: Scoring & Human Decision Gate (Weeks 19–22) *(overlaps Phase 5)*
- Build Scoring Agent — transcript → multi-dimension scorecard with justification text, via the LLM Router.
- Owner Console: Scorecard/Transcript review screen with mandatory Shortlist/Reject/Hold action.
- Audit logging across every automated action, including AI-paused/resumed events.

**Deliverables:** Owner can review a completed interview's scorecard and transcript, and confirm a decision that updates candidate status and triggers the outcome notification (Email).

### Phase 7: Pilot (Weeks 22–26)
- Run one real hiring cycle end-to-end with close Owner monitoring.
- Collect metrics: time-to-form, time-to-interview-invite, candidate satisfaction (especially with the AI interview), transcript/scorecard accuracy spot-checks, **and LLM-router pause frequency** (how often the free tiers ran out during real usage — the key signal for whether the zero-cost policy holds up at real volume).
- Refine interview protocol prompts and etiquette-note copy based on real candidate feedback.

**Deliverables:** Pilot report — including a specific verdict on whether Gemini+Groq free tiers were sufficient for the pilot's actual request volume, and whether the self-hosted speech quality was acceptable to real candidates; go/no-go for broader use.

### Phase 8: Hardening & Expansion (Weeks 27+)
- Add exception-handling robustness (bot join failures, email delivery failures, language-detection edge cases, LLM-router pause frequency if it's higher than expected).
- Revisit platform API access (LinkedIn/Naukri/Internshala partnerships) as a parallel ongoing track.
- Explore Phase 2 features: multi-recruiter accounts, offer generation, additional languages, and re-evaluate the WhatsApp/Sarvam/Recall.ai/Claude trade-offs (§6, [07-Financial-Subscription-Tracking.md §4](./07-Financial-Subscription-Tracking.md)) once there's a revenue case for accepting a small paid tier.

## 2. Team & Roles

| Role | Responsibility |
|---|---|
| Product Owner | Requirements, prioritization, pilot feedback loop |
| Backend Engineer (1–2) | Orchestration, integrations (Zoom, Email, LLM Router) |
| Frontend Engineer (1) | Owner Console + candidate-facing screens |
| ML/Conversational Engineer | Prompt design for requirement parsing, interview logic, scoring rubric; LLM Router fallback logic |
| Voice/Speech + Self-Hosting Engineer | Whisper/AI4Bharat deployment and latency tuning, Vexa self-hosting/ops, code-switching validation — this role now carries more infrastructure/ops responsibility than the original Sarvam-API-integration scope |
| UX Designer | Wireframes, prototypes, candidate-facing localization review |
| Compliance Advisor | Consent flows, EU AI Act / DPDP alignment |
| QA Engineer | End-to-end testing, especially multilingual interview scenarios and LLM-router fallback/pause behavior |

## 3. Milestones Summary

| Milestone | Target Week |
|---|---|
| Owner Console + core integrations live (incl. LLM Router) | Week 2 |
| Requirement intake → form generation working | Week 5 |
| Distribution + response monitoring + resume parsing working | Week 8 |
| Multilingual Email notification working | Week 10 |
| Meeting automation (Zoom/Meet) working | Week 12 |
| Live AI interview functional in all 3 languages (self-hosted stack) | Week 20 |
| Scoring + human decision gate complete | Week 22 |
| Pilot cycle complete | Week 26 |
| Hardening & expansion begins | Week 27+ |

## 4. Testing Strategy

- **Unit/Integration:** Each agent tested independently; particular attention to the STT→LLM→TTS real-time loop for latency and turn-taking correctness on actual self-hosted compute (not assumed numbers).
- **LLM Router Testing:** Explicitly force a Gemini quota exhaustion (e.g., via a test project near its daily limit) to confirm Groq fallback triggers correctly; force both to exhaustion to confirm the pause + single-reminder + auto-resume behavior works exactly as specified (TRD §3.1a) with zero cost incurred.
- **Multilingual Testing:** Dedicated test scripts for English-only, Hindi-only, Marathi-only, and mixed-language (code-switched) interview sessions; native speaker review of transcript accuracy; explicit comparison against the known weaker code-switching performance of the open-source stack.
- **Load/Concurrency:** Verify multiple simultaneous interview sessions (one bot instance per meeting) don't degrade latency, and don't burn through the daily LLM free-tier quota faster than expected.
- **Consent/Compliance Testing:** Verify email opt-in gating works correctly; verify the AI-disclosure step always fires before any interview question is asked.
- **Candidate Usability Testing:** Real fresher/intern volunteers testing the full journey — application, invite, live interview — across all three languages, to catch anxiety points, confusing moments, or speech-quality issues from the self-hosted stack.
- **Owner Usability Testing:** Confirm the requirement-intake chat flow correctly captures intent without excessive clarifying questions, that the Approve/Post/Decision checkpoints feel natural rather than burdensome, and that the AI-paused state (when it occurs) is clearly understandable rather than confusing.

## 5. Rollback / Contingency Plan

- Feature flags per stage (distribution, notification, meeting automation, live interview) so any single automated stage can be disabled and handled manually without breaking the rest of the pipeline.
- If the live AI interview pipeline is unstable for a given language, fall back to English-only or a human-conducted interview for that session rather than risk a poor candidate experience.
- Kill-switch to pause all outbound candidate communications instantly if an issue is detected — note this is distinct from (and can be triggered independently of) the automatic LLM-router quota pause.
- If pilot data (Phase 7) shows the Gemini+Groq free tiers are consistently insufficient for real volume, or the self-hosted speech/meeting-bot quality is unacceptable, the documented paid alternatives in [07-Financial-Subscription-Tracking.md §4](./07-Financial-Subscription-Tracking.md) remain available as an explicit, approved next step — this plan does not assume zero cost forever, only for development/pilot.

## 6. Budget Considerations (High-Level)

Full detail, current free-tier terms, and usage-tracking live in **[07-Financial-Subscription-Tracking.md](./07-Financial-Subscription-Tracking.md)** — treat that document as the source of truth and update it whenever a new dependency is considered. As of this revision, **every item below is $0 in API/subscription cost** for the development/pilot stage; the only real budget line is engineering time for self-hosting/ops (Vexa, Whisper, AI4Bharat) and compute if free-tier hosting proves insufficient.

| Category | Notes |
|---|---|
| LLM (Gemini + Groq free tiers) ✅ | $0 — daily request caps, not a spending cap; router pauses rather than overspending (TRD §3.1a) |
| Speech STT/TTS + Meeting Bot (self-hosted Whisper + AI4Bharat + Vexa, on Oracle Cloud Always Free VM) ✅ | $0 — a permanent free ARM VM (currently 2 OCPU/12GB RAM), not a trial; the right architectural fit since this is a long-running stateful process, not a serverless one (TRD §3.7, §4) |
| Email (Brevo) ✅ | Permanent free tier, 300/day — comfortably above pilot volume |
| Zoom/Google Meet API ✅ | $0 at our scale — free Zoom Basic account covers 1:1 calls up to 40 min (our default interview length is 30 min); Google Meet fallback free with any Google account |
| Resume parsing ✅ | $0 dedicated cost — handled by the LLM Router (already-incurred request budget above) + open-source PDF extraction, no separate vendor |
| Supabase ✅ | Free tier (500MB DB, 1GB storage, 50K MAU) covers pilot scale; re-check before scaling past pilot |
| Cloud infra — app layer (FastAPI/LangGraph backend API, frontend hosting) ✅ | Free tier: Cloud Run or Render for the stateless backend API (requirement parsing, form, distribution, notifications, scoring); Vercel/Netlify free tier for frontend. **Not** used for the voice/meeting-bot pipeline — see row above. |
| Self-hosting engineering/ops time | Not a subscription cost, but real: Vexa, Whisper, and AI4Bharat all need deployment, monitoring, and update effort that a managed SaaS would otherwise absorb — factor into the Voice/Speech + Self-Hosting Engineer role's time budget |
| Design & Dev team | Largest cost center, per roadmap above |
