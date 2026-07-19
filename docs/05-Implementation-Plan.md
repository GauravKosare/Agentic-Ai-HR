# Implementation Plan
## AI Recruiter Agent — Conversational Agentic Hiring Assistant

**Version:** 2.0 (Revised per updated workflow)
**Date:** July 15, 2026

---

## 1. Phased Roadmap

### Phase 0: Foundation & Account Setup (Weeks 1–2)
- Set up Owner Console shell (auth, basic dashboard).
- Connect core external services: SendGrid (email), Meta WhatsApp Business Cloud API (via BSP for speed — e.g., Gupshup/WATI — or direct), Zoom API, Google Meet API.
- Legal/compliance review of consent flows (DPDP-aligned notice/consent, WhatsApp opt-in).

**Deliverables:** Owner can log in; email and WhatsApp test messages send successfully; Zoom instant meeting can be created via API test call.

### Phase 1: Requirement Intake & Form Generation (Weeks 3–5)
- Build Requirement Parser Agent (Claude Sonnet 5) — natural language → structured requisition.
- Build Form Builder Agent — requisition → dynamic candidate form.
- Owner Console: chat intake screen + form preview/approval screen.

**Deliverables:** Owner can describe a role in chat and get an approvable form within minutes.

### Phase 2: Distribution & Response Monitoring (Weeks 5–8) *(overlaps Phase 1)*
- Build Distribution Agent — direct API posting where available (evaluate current partner status for each target platform); Owner-confirm manual flow for LinkedIn/Naukri/Internshala given current access constraints.
- Build Response Monitor Agent — polling/webhook ingestion, dedup, live counter, threshold trigger (default 5).

**Deliverables:** A form posted (via API or Owner-confirmed manual action) with responses flowing into the Pipeline view and triggering the next stage automatically at threshold.

### Phase 3: Multi-Channel, Multilingual Notification (Weeks 8–10)
- Build Notification Agent: Email templates + WhatsApp Business template messages (submit for Meta approval early — ~24h review, but plan buffer).
- Language preference capture on the candidate form; translated template content for English/Hindi/Marathi.
- Interview invite content: date, time, format, time limit, etiquette note.

**Deliverables:** Candidate receives a correctly localized interview invite via both channels upon threshold trigger, with working confirm/reschedule actions.

### Phase 4: Meeting Automation (Weeks 10–12)
- Build Meeting Orchestration Agent — Zoom instant meeting creation at scheduled time (primary), Google Meet fallback.
- Join-link dispatch via Email/WhatsApp shortly before start time.

**Deliverables:** At a scheduled time, a real Zoom meeting is auto-created and the link delivered to a test candidate account.

### Phase 5: Live AI Interview Pipeline (Weeks 12–18) — Highest-Complexity Phase
- Integrate Meeting Bot API (Recall.ai or MeetStream.ai) for cross-platform call joining.
- Integrate Sarvam AI Saaras v3 (STT) and Bulbul V3 (TTS) for real-time Hindi/Marathi/English speech, including code-switching handling.
- Build interview logic agent (Claude Sonnet 5): resume-grounded question generation, adaptive follow-ups, standard protocol (opening → resume Qs → role Qs → adaptive follow-ups → closing).
- Build disclosure step (spoken + written) confirming AI interviewer + recording consent at meeting start.
- Extensive internal testing across all three languages and common code-switching patterns before any real candidate use.

**Deliverables:** A functioning end-to-end AI-conducted interview in a test meeting, in each of English, Hindi, and Marathi, with acceptable latency (~1 second conversational round-trip) and transcript accuracy validated against manual review.

### Phase 6: Scoring & Human Decision Gate (Weeks 17–20) *(overlaps Phase 5)*
- Build Scoring Agent — transcript → multi-dimension scorecard with justification text.
- Owner Console: Scorecard/Transcript review screen with mandatory Shortlist/Reject/Hold action.
- Audit logging across every automated action.

**Deliverables:** Owner can review a completed interview's scorecard and transcript, and confirm a decision that updates candidate status and triggers the outcome notification.

### Phase 7: Pilot (Weeks 20–24)
- Run one real hiring cycle end-to-end with close Owner monitoring.
- Collect metrics: time-to-form, time-to-interview-invite, candidate satisfaction (especially with the AI interview), transcript/scorecard accuracy spot-checks.
- Refine interview protocol prompts and etiquette-note copy based on real candidate feedback.

**Deliverables:** Pilot report; go/no-go for broader use.

### Phase 8: Hardening & Expansion (Weeks 25+)
- Add exception-handling robustness (bot join failures, WhatsApp delivery failures, language-detection edge cases).
- Revisit platform API access (LinkedIn/Naukri/Internshala partnerships) as a parallel ongoing track.
- Explore Phase 2 features: multi-recruiter accounts, offer generation, additional languages.

## 2. Team & Roles

| Role | Responsibility |
|---|---|
| Product Owner | Requirements, prioritization, pilot feedback loop |
| Backend Engineer (1–2) | Orchestration, integrations (Zoom, WhatsApp, Meeting Bot API, Sarvam AI) |
| Frontend Engineer (1) | Owner Console + candidate-facing screens |
| ML/Conversational Engineer | Prompt design for requirement parsing, interview logic, scoring rubric |
| Voice/Speech Integration Engineer | Sarvam AI STT/TTS integration, latency tuning, code-switching validation |
| UX Designer | Wireframes, prototypes, candidate-facing localization review |
| Compliance Advisor | Consent flows, WhatsApp template compliance, EU AI Act / DPDP alignment |
| QA Engineer | End-to-end testing, especially multilingual interview scenarios |

## 3. Milestones Summary

| Milestone | Target Week |
|---|---|
| Owner Console + core integrations live | Week 2 |
| Requirement intake → form generation working | Week 5 |
| Distribution + response monitoring working | Week 8 |
| Multilingual notification (Email + WhatsApp) working | Week 10 |
| Meeting automation (Zoom/Meet) working | Week 12 |
| Live AI interview functional in all 3 languages | Week 18 |
| Scoring + human decision gate complete | Week 20 |
| Pilot cycle complete | Week 24 |
| Hardening & expansion begins | Week 25+ |

## 4. Testing Strategy

- **Unit/Integration:** Each agent tested independently; particular attention to the STT→LLM→TTS real-time loop for latency and turn-taking correctness.
- **Multilingual Testing:** Dedicated test scripts for English-only, Hindi-only, Marathi-only, and mixed-language (code-switched) interview sessions; native speaker review of transcript accuracy.
- **Load/Concurrency:** Verify multiple simultaneous interview sessions (one bot instance per meeting) don't degrade latency.
- **Consent/Compliance Testing:** Verify WhatsApp opt-in gating works correctly; verify the AI-disclosure step always fires before any interview question is asked.
- **Candidate Usability Testing:** Real fresher/intern volunteers testing the full journey — application, invite, live interview — across all three languages, to catch anxiety points or confusing moments.
- **Owner Usability Testing:** Confirm the requirement-intake chat flow correctly captures intent without excessive clarifying questions, and that the Approve/Post/Decision checkpoints feel natural rather than burdensome.

## 5. Rollback / Contingency Plan

- Feature flags per stage (distribution, notification, meeting automation, live interview) so any single automated stage can be disabled and handled manually without breaking the rest of the pipeline.
- If the live AI interview pipeline is unstable for a given language, fall back to English-only or a human-conducted interview for that session rather than risk a poor candidate experience.
- Kill-switch to pause all outbound candidate communications instantly if an issue is detected.

## 6. Budget Considerations (High-Level)

| Category | Notes |
|---|---|
| Claude API usage | Scales with requirement parsing volume + interview minutes |
| Sarvam AI (STT/TTS) | Pay-as-you-go; budget per interview minute across three languages |
| Meeting Bot API (Recall.ai/MeetStream.ai) | Per-meeting-minute cost |
| WhatsApp Business (Cloud API / BSP) | Per-conversation/template message cost; BSP platform fee if used |
| Zoom/Google Meet API | Standard developer tier costs |
| Resume parsing (Affinda or alternative) | Per-parse cost |
| Cloud infra | Scales with concurrent interview volume |
| Design & Dev team | Largest cost center, per roadmap above |
