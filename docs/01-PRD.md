# Product Requirements Document (PRD)
## AI Recruiter Agent — Conversational Agentic Hiring Assistant

**Version:** 3.0 (Revised for zero-cost stack and Email-only candidate messaging)
**Date:** July 19, 2026
**Owner:** HR Tech / Talent Acquisition Product Team

---

## 1. Purpose & Vision

Build a single-operator agentic AI system, delivered as a **web application** (responsive, browser-based — no install required for either the Owner or candidates), where a recruiter (the "Owner") creates one recruitment platform account, grants the AI Agent access, and then simply tells it *what* to hire for (role, quantity, location type, seniority, must-have skills, etc.). From that point, the AI Agent autonomously:

1. Drafts and floats job/internship forms to connected platforms.
2. Monitors incoming responses continuously.
3. Once a minimum response threshold is met, contacts candidates via Email with interview logistics.
4. Auto-creates a Zoom/Google Meet meeting at the scheduled time and invites participants.
5. Joins the meeting and conducts a structured, resume-grounded interview — in English, Hindi, or Marathi — following a standard interview protocol.
6. Produces a scorecard for the Owner to review and make the final call.

This is a fundamental shift from an enterprise multi-stakeholder ATS toward a **single-recruiter, conversation-driven, end-to-end agentic assistant**.

## 2. Problem Statement

Independent recruiters, small hiring teams, and founders running lean hiring cycles don't have the bandwidth for full-time sourcing, screening, scheduling, and first-round interviewing. They need to be able to state a requirement in plain language and have an AI agent execute the entire pipeline up to (but not including) the final hiring decision.

## 3. Goals

- Let the Owner describe a hiring need conversationally and have the AI translate it into a ready-to-post form within minutes.
- Automate distribution, response monitoring, and candidate communication end-to-end.
- Conduct real, live, voice-based first-round interviews via video call — not just async chat/text — with adaptive, resume-aware questioning.
- Support English, Hindi, and Marathi natively, including candidates who code-switch between them.
- Keep the Owner as the final decision-maker; the AI never makes a hire/reject call unsupervised.

## 4. Non-Goals

- The AI does not autonomously finalize any accept/reject decision — every "reject" or "select" status change requires Owner confirmation.
- The AI does not scrape or use unofficial/unauthorized methods to access platforms where it lacks legitimate posting rights.
- This is not a multi-recruiter enterprise ATS in v1 — it is scoped to a single Owner account operating the agent.

## 5. Key User Story (Primary Flow)

> *As the Owner, I tell the AI: "I need 3 backend development interns, remote, 3-month duration, must know Python and SQL, stipend ₹15,000/month." The AI drafts a form, shows it to me for one-click approval, posts it to my connected platforms, watches for responses, and once at least 5 candidates apply, reaches out to each with interview details in their preferred language over email. At the scheduled time, it spins up a Meet/Zoom call, joins as the interviewer, conducts the interview based on their resume and live answers, and hands me a scorecard afterward so I can decide who moves forward.*

## 6. Scope (Phase 1 MVP)

1. **Conversational Requirement Intake** — Owner describes the role in natural language (chat or simple form); AI extracts structured requisition fields (role, count, work mode, duration, compensation, skills, eligibility).
2. **AI-Generated Application Form** — Dynamic form built from the requisition; Owner reviews/edits before it goes live (one-click approve, not fully silent).
3. **Platform Distribution** — Posts to platforms where the Owner has legitimate account/API access; where only manual posting is available, the AI prepares the exact content and the Owner does a single confirming action.
4. **Continuous Response Monitoring** — Polls/webhooks connected sources; triggers next stage once **≥5 responses** are received (configurable threshold).
5. **Interview Invitation (Email)** — Sends interview date, time, format, time limit, and interview etiquette/protocol via Email, in the candidate's selected language. (WhatsApp was evaluated and deliberately excluded — see §8 and [07-Financial-Subscription-Tracking.md](./07-Financial-Subscription-Tracking.md).)
6. **Automated Meeting Creation** — At the scheduled time (set by the Owner per requisition or per candidate; capped at 40 minutes on the free Zoom tier), the AI creates a Zoom (primary) or Google Meet (secondary) instant meeting and sends the join link via Email.
7. **Live AI-Conducted Interview** — A meeting bot joins the call, greets the candidate, conducts a structured interview referencing the candidate's resume and their live answers, in English/Hindi/Marathi with natural code-switching support.
8. **Scorecard Generation** — Structured, multi-dimension scorecard with transcript, delivered to the Owner's dashboard.
9. **Human Decision Gate** — Owner reviews and confirms shortlist/reject; no automated final decision.

### Phase 2 (Future)
- Multi-recruiter/team accounts.
- Additional languages beyond English/Hindi/Marathi.
- Offer letter generation + e-signature + onboarding handoff.
- Deeper platform partner API integrations as they're secured (see TRD for current status).

## 7. Functional Requirements

| ID | Requirement | Priority |
|---|---|---|
| FR-1 | AI shall parse a natural-language hiring brief into a structured requisition (role, quantity, work mode, duration, compensation, skills, eligibility) | P0 |
| FR-2 | AI shall auto-generate an application form matching the requisition, editable by the Owner before publishing | P0 |
| FR-3 | System shall post/float the approved form to connected platforms via legitimate API or Owner-confirmed manual posting | P0 |
| FR-4 | System shall continuously monitor and count incoming responses per requisition | P0 |
| FR-5 | System shall trigger candidate outreach automatically once the response threshold (default 5) is reached | P0 |
| FR-6 | System shall send interview invitations via Email containing date, time, format, time limit, and etiquette/protocol instructions | P0 |
| FR-7 | System shall detect/accept candidate's language preference (English, Hindi, Marathi) and communicate accordingly | P0 |
| FR-8 | System shall auto-create a Zoom (primary) or Google Meet (fallback) instant meeting at the scheduled interview time, within the free-tier 40-minute limit | P0 |
| FR-9 | System shall send the meeting join link via Email | P0 |
| FR-10 | AI agent shall join the live meeting as a participant and conduct a structured, resume-grounded interview with real-time speech in the candidate's language | P0 |
| FR-11 | System shall record the interview, generate a transcript, and produce a rubric-based scorecard | P0 |
| FR-12 | Owner shall review every scorecard and confirm shortlist/reject — no fully autonomous final decision | P0 |
| FR-13 | System shall log every automated action (post, message sent, meeting created, score generated, AI paused/resumed on free-tier quota exhaustion) for audit | P0 |
| FR-14 | System shall track and honor candidate consent for data processing and communications | P0 |
| FR-15 | System shall use only free-tier or free/open-source, self-hosted tools and services for the development/pilot stage; if an LLM free tier is exhausted, the system shall pause AI-dependent actions and notify the Owner rather than incur cost | P0 |

## 8. Non-Functional Requirements

- **Compliance:**
  - **EU AI Act:** High-risk obligations for employment/recruitment AI (documentation, bias testing, human oversight, transparency, registration) — deferred from 2 Aug 2026 to **2 December 2027** under the Digital Omnibus (final Council approval 29 June 2026). Build to the full requirement set now regardless of the exact enforcement date.
  - **India DPDP Act:** Rules notified 13–14 November 2025; phased — Data Protection Board active now, Consent Manager framework live from 13 November 2026, full substantive obligations (notice, consent, breach handling) enforceable from **13 May 2027**. Design consent/notice flows to this standard from day one.
  - **Meeting recording consent:** Candidates must be clearly informed the interview is AI-conducted and recorded before the meeting starts (both verbally at join and in the pre-interview communication).
- **Platform ToS risk:** Automated posting/interaction on third-party recruitment platforms via anything other than an officially sanctioned API or the Owner's own manual action carries Terms-of-Service risk, independent of data-access legality. Default to "AI drafts, human confirms" wherever official API access isn't in place.
- **Cost policy:** Every tool/service used must run on a genuine free tier or free/open-source self-hosted software for the development/pilot stage — no paid subscription is required. Where an LLM's free-tier quota is exhausted, the system pauses AI-dependent work and notifies the Owner rather than falling through to a paid model (see FR-15, TRD §3.1a).
- **Latency:** Real-time interview STT/TTS round-trip should stay under ~1 second to feel conversational; realistically ~0.5–2 seconds on the CPU-only Oracle Cloud Always Free VM hosting the speech pipeline (see TRD §3.7) — measure and validate in Phase 5 rather than assuming the ideal figure.
- **Scalability:** Support concurrent interviews across multiple requisitions (one bot instance per meeting).
- **Availability:** 99.5% uptime during active hiring/interview windows.
- **Security:** PII encrypted at rest/in transit; role-based access enforced via Postgres Row Level Security (Supabase) so an Owner can only ever access their own data; recordings and resumes stored in private, signed-URL-only object storage with defined retention.
- **Auditability:** Every automated decision reconstructable (who/what/when/why).

## 9. Success Metrics

- Time from "requirement stated" to "form live" under 15 minutes.
- Time from "5th response received" to "interview invite sent" under 1 hour.
- Candidate satisfaction with the AI interview experience ≥ 4/5.
- Owner override rate on AI scorecards tracked and reviewed monthly (informs rubric tuning).
- Zero compliance violations (consent, unauthorized platform actions, discrimination complaints).

## 10. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Automated posting/interaction on platforms violates ToS even on the Owner's own account | Restrict full automation to platforms with official employer/recruiter API access; everywhere else, AI prepares content and Owner performs the actual posting action |
| LinkedIn/Naukri/Internshala API access is slow/gated (verified: LinkedIn Partner approval 3–6 months, <10% approval rate, AWLI closed to new partners since Oct 2025; Internshala has no confirmed public employer API; Naukri is enterprise-contract-gated) | Launch with manual/CSV posting + Owner-confirmed actions for these three; treat deeper API integration as a parallel partnership track, not a Phase 1 dependency |
| Candidate discomfort with an AI-conducted interview | Always disclose upfront (message + verbal at meeting join) that the interviewer is AI and the session is recorded; offer a human-interview fallback path |
| Multilingual accuracy errors (especially Hindi/Marathi code-switching) mislead scoring — **elevated risk**: the Whisper-family STT (Groq-hosted) + AI4Bharat TTS (self-hosted) stack, chosen for zero cost, is measurably weaker on code-switching than the purpose-built commercial option originally specified | Dedicated multilingual/code-switching test pass before any real candidate use (TRD §3.7); include human review of transcript alongside score, not score alone; fall back to English-only or human-conducted interview if accuracy is unacceptable for a session |
| Legal risk from fully automated rejection | Human-in-loop gate before any final adverse action |
| Meeting bot fails to join or drops mid-interview | Auto-retry join; if failure persists, auto-reschedule with apology notification; log incident |
| Groq outage or account issue simultaneously breaks the LLM fallback and STT (both hosted by Groq) mid-interview | No second STT provider configured yet; system distinguishes this failure (`TranscriptionUnavailable`) from quota exhaustion so it can be handled explicitly (e.g. reschedule) rather than crash — revisit if pilot data shows this occurring often (TRD §3.7, [07-Financial-Subscription-Tracking.md](./07-Financial-Subscription-Tracking.md)) |
| Free-tier LLM quota (Gemini + Groq) exhausted during a busy day, pausing AI-dependent actions | System pauses gracefully and notifies the Owner once rather than silently failing or incurring cost (TRD §3.1a); resumes automatically at next quota reset; track pause frequency as a signal for whether a small paid tier is warranted |
| Dropping WhatsApp narrows candidate reach for candidates who prefer it over email | Documented, deliberate trade-off for zero recurring cost (see [07-Financial-Subscription-Tracking.md](./07-Financial-Subscription-Tracking.md)); revisit as an approved paid addition if reach data shows it's needed |

## 11. Assumptions

- The Owner has (or will obtain) legitimate accounts/API access on the platforms they intend to use.
- The Owner sets interview time slots; the system does not unilaterally choose interview times without Owner-defined windows.
- Volume is suited to a single-recruiter tool (dozens to low hundreds of candidates per requisition), not enterprise-scale campus hiring in Phase 1.
