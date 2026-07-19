# AI Recruiter Agent

**A conversational, agentic AI hiring assistant** that takes a recruiter from stating a hiring need in plain language all the way through form generation, candidate sourcing, multilingual interview scheduling, live AI-conducted interviews, and scorecard delivery — with a human decision-maker always in the loop for final calls.

> **Status:** Pre-development / Design phase. This repository currently contains the full product, technical, and design specification produced before implementation begins.

---

## What This Project Does

1. **You describe the role** — headcount, work mode, duration, skills, compensation — in plain language.
2. **The AI drafts a candidate application form**, which you review and approve with one click.
3. **The AI posts/distributes the form** to connected platforms (directly via API where access exists, or with your one-click confirmation where it doesn't).
4. **The AI monitors responses** and automatically triggers candidate outreach once a response threshold is met.
5. **Interview invitations** (date, time, format, time limit, etiquette protocol) go out via **Email and WhatsApp Business**, in the candidate's preferred language.
6. **At the scheduled time**, the AI auto-creates a Zoom (or Google Meet) instant meeting and sends the join link.
7. **A meeting bot joins the call** and conducts a live, structured, resume-grounded interview — in **English, Hindi, or Marathi**, including natural code-switching between them.
8. **A scorecard and transcript** are generated and handed to you for the final shortlist/reject/hold decision — the AI never finalizes this on its own.

## Documentation

All product, technical, and design specifications live in [`/docs`](./docs):

| Document | Description |
|---|---|
| [01 — Product Requirements Document](./docs/01-PRD.md) | Vision, goals, scope, functional & non-functional requirements, compliance posture, risks |
| [02 — Technical Requirements Document](./docs/02-TRD.md) | System architecture, agent breakdown, verified tech stack, integration access status |
| [03 — Workflow](./docs/03-Workflow.md) | End-to-end process flow (with diagram), stage-by-stage breakdown, exception handling |
| [04 — UI/UX Design Brief](./docs/04-UIUX-Design-Brief.md) | Owner Console and candidate-facing design direction, key screens, tone of voice |
| [05 — Implementation Plan](./docs/05-Implementation-Plan.md) | Phased roadmap, team roles, milestones, testing strategy, rollback plan |
| [06 — Backend Schema](./docs/06-Backend-Schema.md) | Full PostgreSQL schema (DDL), entity relationships, design notes |

## Key Technology Decisions

| Capability | Chosen Tech | Why |
|---|---|---|
| Orchestration / reasoning | Claude Sonnet 5 (Anthropic API) | Requirement parsing, form generation, interview logic, scoring |
| Multilingual speech (STT/TTS) | Sarvam AI (Saaras v3 / Bulbul V3) | Purpose-built for Hindi/Marathi/English, handles natural code-switching |
| Live meeting join | Recall.ai or MeetStream.ai (Meeting Bot API) | Cross-platform (Zoom/Meet/Teams), no host permission required |
| Meeting creation | Zoom API (primary), Google Meet API (fallback) | Zoom has more mature instant-meeting support |
| Candidate messaging | Meta WhatsApp Business Cloud API + SendGrid | Cloud API is the only supported WhatsApp path since Oct 2025 (on-premise deprecated) |
| Resume parsing | Affinda (or RChilli/Textkernel as lower-cost alternatives) | Still active, 100+ fields, 50+ languages |
| Data store | PostgreSQL + pgvector | Structured data + resume/JD embedding similarity |

See [02-TRD.md](./docs/02-TRD.md) for the full architecture and verified integration status as of July 2026.

## Important Constraints Baked Into This Design

- **Platform posting is not fully autonomous everywhere.** LinkedIn, Naukri, and Internshala do not currently offer easy self-serve API access for job posting (LinkedIn Partner approval is slow/selective and closed new "Apply with LinkedIn" partners as of Oct 2025; Internshala has no confirmed public employer API; Naukri access is enterprise-contract-gated). Where API access isn't in place, the system prepares content for a one-click, Owner-confirmed manual post — it does not silently automate actions on third-party platforms.
- **No fully autonomous hiring decisions.** Every shortlist/reject/hold status requires explicit Owner confirmation. This is a deliberate design choice, not just a current-best-practice suggestion — it aligns with emerging regulatory expectations for AI in employment decisions (see Compliance below).
- **Candidates are always told they're speaking with an AI interviewer** and that the session is recorded, both in writing before the interview and verbally at the start of the call.

## Compliance Posture

- **EU AI Act:** Recruitment AI is classified high-risk. Full obligations (documentation, bias testing, human oversight, transparency, registration) were deferred from 2 Aug 2026 to **2 December 2027** under the Digital Omnibus — this project is designed to the full requirement set regardless of the exact enforcement date.
- **India DPDP Act:** Rules notified Nov 2025; substantive obligations (notice, consent, breach handling) become enforceable **13 May 2027**. Consent flows in this design already meet that standard.
- **WhatsApp messaging:** Uses Meta's approved Cloud API and pre-approved message templates with explicit candidate opt-in.

*This is not legal advice. Consult qualified counsel before launch, particularly regarding jurisdiction-specific employment and data protection law.*

## Repository Structure

```
ai-recruiter-agent/
├── README.md              ← you are here
├── LICENSE                ← proprietary, all rights reserved
├── docs/
│   ├── 01-PRD.md
│   ├── 02-TRD.md
│   ├── 03-Workflow.md
│   ├── 04-UIUX-Design-Brief.md
│   ├── 05-Implementation-Plan.md
│   └── 06-Backend-Schema.md
├── src/                    ← (to be added — application source code)
├── CHANGELOG.md
└── .gitignore
```

## Roadmap Snapshot

See [05-Implementation-Plan.md](./docs/05-Implementation-Plan.md) for full detail. High level:

- **Phase 0–2:** Foundation, requirement intake, form generation, distribution, response monitoring
- **Phase 3–4:** Multilingual notifications (Email/WhatsApp), meeting automation
- **Phase 5–6:** Live AI interview pipeline (highest complexity), scoring, human decision gate
- **Phase 7–8:** Pilot, hardening, expansion

## License

This project is **proprietary and confidential**. All rights reserved. See [LICENSE](./LICENSE) for full terms. No part of this repository may be copied, distributed, or used without explicit written permission from the owner.

## Contact

For questions about this project, contact the repository owner directly.
