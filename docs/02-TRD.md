# Technical Requirements Document (TRD)
## AI Recruiter Agent — Conversational Agentic Hiring Assistant

**Version:** 2.0 (Revised per updated workflow)
**Date:** July 15, 2026

---

## 1. System Overview

A single orchestrated AI agent (built on Claude) manages the full pipeline from natural-language requirement intake through live interview conduction, calling out to specialized sub-services (form generation, platform posting, messaging, meeting creation, meeting-bot interviewing, multilingual speech) at each stage. A lightweight dashboard gives the Owner visibility and control (approve form, confirm decisions).

## 2. High-Level Architecture

```
                     ┌───────────────────────────────┐
                     │   Owner (Recruiter) Dashboard   │
                     │   Chat/Form intake + Review UI  │
                     └───────────────┬───────────────┘
                                     │
                     ┌───────────────▼───────────────┐
                     │   Orchestrator Agent (Claude    │
                     │   Sonnet 5 + LangGraph FSM)      │
                     └───────────────┬───────────────┘
        ┌───────────────┬────────────┼────────────┬───────────────┐
        ▼               ▼            ▼            ▼               ▼
   Requirement      Form Builder   Distribution  Response      Notification
   Parser Agent      Agent         Agent         Monitor       Agent
        │               │            │            │               │
        ▼               ▼            ▼            ▼               ▼
   Structured      Dynamic Form   Platform APIs / Postgres    Email (SendGrid) +
   Requisition      (React/JSON)   Owner-confirm  (candidates,  WhatsApp Business
   (Postgres)       Schema         posting        responses)    Cloud API

                     ┌───────────────────────────────┐
                     │   Meeting Orchestration Agent    │
                     └───────────────┬───────────────┘
        ┌───────────────┬────────────┼────────────┬───────────────┐
        ▼               ▼            ▼            ▼               ▼
   Zoom API         Google Meet   Meeting Bot API  Sarvam AI      Scoring
   (instant          API           (Recall.ai /     (STT/TTS:      Agent
   meeting,          (fallback)    MeetStream.ai —   Hindi/Marathi/ (Claude
   primary)                        joins call,        English)      Sonnet 5)
                                    streams audio)
                                         │
                                         ▼
                                  Interview Transcript
                                  + Scorecard → Dashboard
                                  → Owner Confirms Decision
```

## 3. Core Components

### 3.1 Requirement Parser Agent
- Takes the Owner's natural-language brief (chat message or short form) and extracts structured fields: role title, quantity, work mode (onsite/remote/hybrid), duration, compensation/stipend, required skills, eligibility criteria, seniority level.
- Model: **Claude Sonnet 5** (balanced cost/quality for structured extraction).
- Output validated against a JSON schema before proceeding; ambiguous fields trigger a single clarifying question back to the Owner (not silent assumption).

### 3.2 Form Builder Agent
- Generates a candidate-facing application form (fields matched to requisition: resume upload, basic info, skill self-assessment, availability, language preference).
- Rendered as a hosted web form (React) or via a form-service API (e.g., Typeform API) for faster time-to-market.
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

### 3.5 Notification Agent (Email + WhatsApp)
- **Email:** SendGrid (or similar) for interview invitations, confirmations, status updates.
- **WhatsApp:** **Meta WhatsApp Business Cloud API** — the only supported path since the on-premise API was deprecated 23 October 2025. Self-serve setup, business verification typically takes 1–3 business days. Requires:
  - Pre-approved message templates (Meta reviews within ~24h) for interview details, reminders, and status updates.
  - Explicit opt-in captured at application before any WhatsApp outreach.
  - A Business Solution Provider (e.g., Gupshup, WATI, Twilio) can be used instead of raw Cloud API to skip building webhook/template-management infrastructure from scratch — recommended for faster MVP delivery.
- Messages include interview date, time, format, duration/time limit, and a plain-language etiquette/protocol note (camera on, quiet environment, ID verification, etc.), delivered in the candidate's selected language.

### 3.6 Meeting Orchestration Agent
- At the scheduled time, creates an **instant Zoom meeting** via the Zoom API (primary — Zoom's API/SDK support for instant meeting creation and bot joining is the most mature) or a Google Meet link (secondary/fallback where the candidate prefers Meet).
- Sends the join link via Email + WhatsApp shortly before the scheduled time.

### 3.7 Meeting Bot / Live Interview Agent
- Uses a **Meeting Bot API** (Recall.ai or MeetStream.ai) to join the Zoom/Meet call as a participant — no host permission required, works across Zoom/Meet/Teams through one integration, streams real-time audio/video.
- Real-time audio pipeline: candidate speech → **Sarvam AI Saaras v3 STT** → transcribed text → **Claude Sonnet 5** (question generation/adaptive follow-up, grounded in the candidate's resume + prior answers) → **Sarvam AI Bulbul V3 TTS** → spoken response back into the meeting.
- Sarvam AI is purpose-built for Hindi/Marathi/English **including natural code-switching** (candidates mixing languages mid-sentence), which general-purpose STT/TTS (e.g., Whisper + generic TTS) handles poorly for Indian languages — this directly addresses the multilingual requirement.
- Follows a standard interview protocol: opening/rapport → resume-specific questions → role-relevant technical/behavioral questions → adaptive follow-ups → closing.
- Candidate is informed at meeting start (spoken + earlier written notice) that the interviewer is AI and the session is recorded.

### 3.8 Scoring Agent
- Generates a multi-dimension scorecard (communication, technical depth, problem-solving, role fit) with justification text, using **Claude Sonnet 5** against the transcript.
- Full transcript + audio/video retained per data retention policy.

### 3.9 Human Decision Gate
- Owner Dashboard surfaces every scorecard + transcript.
- Owner must actively confirm shortlist/reject — no status is ever finalized without this action.
- Any override of AI's implied recommendation requires a short justification note (logged for audit).

### 3.10 Audit & Compliance Layer
- Every automated action (form generated, posted, message sent, meeting created, score generated) logged immutably: `entity, action, actor(system/user), timestamp, details`.
- Consent status tracked per candidate per channel (data processing, email, WhatsApp, AI interview).

## 4. Tech Stack (Updated & Verified)

| Layer | Technology |
|---|---|
| Orchestration | LangGraph (Python) or custom FSM |
| LLM | **Claude Sonnet 5** (primary — requirement parsing, form generation, interview dialogue, scoring); Claude Haiku 4.5 for lightweight/high-volume tasks (e.g., dedup checks, simple classification) |
| Resume Parsing | Affinda API (still active, 100+ fields/50+ languages) or RChilli/Textkernel as lower-cost alternatives |
| Form Hosting | Custom React form or Typeform API |
| Primary DB | PostgreSQL |
| Vector DB (resume/JD matching) | pgvector (Postgres extension) or Pinecone |
| Email | SendGrid |
| WhatsApp | Meta WhatsApp Business Cloud API, direct or via a BSP (Gupshup/WATI/Twilio) for faster setup |
| Video Meeting Creation | Zoom API (primary, instant meeting creation + mature SDK); Google Meet API (secondary/fallback) |
| Meeting Bot (AI joins call) | Recall.ai or MeetStream.ai Meeting Bot API — cross-platform (Zoom/Meet/Teams), no host permission needed |
| Speech (STT) | **Sarvam AI Saaras v3** — Hindi/Marathi/English with code-switching, <150ms time-to-first-token |
| Speech (TTS) | **Sarvam AI Bulbul V3** — Hindi/Marathi/English, sub-250ms first-byte streaming, 35+ voices |
| Backend API | FastAPI (Python) |
| Frontend (Owner Dashboard) | React + TypeScript, Tailwind |
| Auth | OAuth2 / simple email-password for single-Owner MVP |
| Hosting | AWS/GCP, containerized (Docker) |
| Monitoring | Grafana + Prometheus, Sentry |
| CI/CD | GitHub Actions |

## 5. Integration Points — Verified July 2026

| Integration | Purpose | Access Reality |
|---|---|---|
| LinkedIn Talent Solutions API | Post jobs, pull applicants | Gated, slow, AWLI closed to new partners since Oct 2025 — treat as Owner-manual for MVP |
| Internshala | Post internships | No confirmed public API — Owner-manual/CSV for MVP |
| Naukri Recruiter API | Post jobs | Enterprise-contract-gated — Owner-manual for MVP |
| Meta WhatsApp Business Cloud API | Candidate messaging | Self-serve, live in days; on-premise API deprecated Oct 2025 |
| SendGrid | Email | Standard self-serve |
| Zoom API | Instant meeting creation | Self-serve developer API, mature instant-meeting support |
| Google Meet API | Fallback meeting creation | Self-serve but thinner instant-meeting support than Zoom |
| Recall.ai / MeetStream.ai | Meeting bot join + audio stream | Self-serve, cross-platform, no host permission required |
| Sarvam AI | STT/TTS Hindi/Marathi/English | Self-serve API, free tier + pay-as-you-go |
| Affinda | Resume parsing | Self-serve, 14-day free trial, consumption-based pricing |

## 6. Data Flow Summary

1. Owner states requirement (chat/form) → Requirement Parser Agent → structured requisition stored.
2. Form Builder Agent generates form → Owner approves → Distribution Agent posts (API where possible, Owner-confirmed manual otherwise).
3. Response Monitor Agent tracks applications → fires event at ≥5 responses.
4. Notification Agent sends interview invite (Email + WhatsApp, candidate's language) with date/time/format/protocol.
5. Candidate confirms → Meeting Orchestration Agent creates Zoom/Meet instant meeting at scheduled time → sends join link.
6. Meeting Bot joins → real-time STT (Sarvam) → Claude Sonnet 5 interview logic → real-time TTS (Sarvam) → live conversation.
7. Scoring Agent generates scorecard from transcript → surfaced on Owner Dashboard.
8. Owner reviews and confirms final decision → status updated → candidate notified.

## 7. Performance Requirements

- Requirement-to-form-draft: under 2 minutes of processing time.
- Real-time interview STT→LLM→TTS round trip: target under ~1 second for natural conversational pacing.
- WhatsApp/Email dispatch after threshold trigger: under 5 minutes.
- Meeting bot join time after meeting creation: under 30 seconds.

## 8. Failure Handling

- If the meeting bot fails to join: auto-retry twice, then notify Owner and auto-reschedule candidate with an apology message.
- If WhatsApp delivery fails (e.g., candidate not opted in or number invalid): fall back to email-only and flag for Owner review.
- If platform posting API call fails: retry with backoff; if persistent, surface to Owner as a manual-action item.
