# UI/UX Design Brief
## AI Recruiter Agent — Conversational Agentic Hiring Assistant

**Version:** 3.0 (Revised for zero-cost stack: Email-only messaging, AI-paused state)
**Date:** July 19, 2026

---

## 1. Design Objective

Delivered as a **single responsive web application** (React) with two experiences as distinct route groups within it — not two separate products:
1. **Owner Console** — a conversational, low-friction control surface where a single recruiter states requirements, approves forms, and reviews scorecards. Should feel like directing an assistant, not operating enterprise software. Login/session via Supabase Auth.
2. **Candidate Experience** — application form, interview invitation, and the live AI interview itself, reached via unauthenticated links (no candidate account/login required). Must feel transparent, respectful, and calm, especially since the interviewer is AI.

## 2. Target Users & Contexts

| Interface | User | Device | Context |
|---|---|---|---|
| Owner Console | Solo recruiter / founder / small hiring team | Desktop primary, mobile secondary | Quick check-ins throughout the day; occasional deep review sessions |
| Candidate Application Form | Fresher/intern applicant | Mobile-first | Applying on the go, often from a job platform link |
| Candidate Interview | Fresher/intern applicant | Desktop or mobile browser/Zoom app | Higher-anxiety moment — first "real" interaction with the process |

## 3. Design Principles

- **Conversation-first, not form-first:** the Owner's primary input mode is natural language; structured forms are a fallback/edit layer, not the main interaction.
- **One-click confirmation, never silent action:** every externally visible action (form goes live, message sent to a platform outside official API, final candidate decision) has a clear human confirmation step, visibly presented — this builds trust that the AI isn't acting unsupervised where it matters.
- **Transparency for candidates:** always disclose AI involvement — in the form, in the interview invite, and verbally at the start of the interview.
- **Calm, low-anxiety candidate tone:** especially around the live interview, since this is the most novel and potentially stressful touchpoint.
- **Multilingual by design, not by afterthought:** language selection is a first-class, early step in the candidate journey, not buried in settings.
- **Accessibility:** WCAG 2.1 AA minimum on both interfaces.

## 4. Owner Console — Key Screens

### 4.1 Requirement Intake (Chat Interface)
- A chat-style input: "Tell me what you're hiring for" with example prompts shown ("3 backend interns, remote, 3 months, ₹15k stipend").
- AI responds with a structured summary card ("Here's what I've got — 3x Backend Development Intern, Remote, 3 months, ₹15,000/month, Python + SQL required") and asks at most one clarifying question if needed.
- "Looks good, generate form" primary action.

### 4.2 Form Preview & Approval
- Live preview of the candidate-facing form exactly as it will appear.
- Inline edit capability (add/remove/reword fields) before approval.
- Clear "Approve & Post" button — this is the human-confirmation checkpoint before anything goes external.

### 4.3 Distribution Status Panel
- Per-platform status: "Posted automatically" (API-connected platforms) vs. "Ready to post — click to copy and post on [Platform]" (manual-confirm platforms), with the exact listing text ready to paste.
- Response counter per requisition, live-updating, with a visible progress toward the 5-response threshold.

### 4.3a AI Status Indicator (system-wide)
- A persistent, small status chip in the Owner Console header: "AI active" (default) or "AI paused — free quota reached, resuming at [time]" when the LLM Router (TRD §3.1a) has exhausted both Gemini's and Groq's free tiers for the day.
- While paused, any screen that would trigger an AI action (approve form, send invite, view scorecard-in-progress) shows an inline note rather than failing silently — e.g., "This will process automatically once the AI resumes at [time]." Non-AI actions (viewing data, manual posting, confirming a decision on an already-generated scorecard) remain fully usable.

### 4.4 Pipeline / Candidate List
- Simple list/table per requisition: candidate name, source platform, response date, status (applied → invited → interviewed → reviewed → decided).
- Filter by status, source, language preference.

### 4.5 Scorecard & Transcript Review
- Candidate detail view: resume side-by-side with parsed fields, full interview transcript, multi-dimension scorecard with plain-language justification per dimension.
- Prominent, unavoidable **Shortlist / Reject / Hold** buttons — this is the terminal human decision point, never bypassed.
- Optional note field for override justification if the Owner disagrees with the AI's implied read of the interview.

### 4.6 Settings
- Response threshold configuration (default 5).
- Connected accounts (platforms, Email, Zoom/Google Meet).
- Default interview time-limit and etiquette-note template (editable; capped guidance at 40 minutes to stay within the free Zoom tier).
- Supported languages toggle (English/Hindi/Marathi on by default).
- Today's AI usage: simple view of Gemini/Groq free-tier requests used vs. daily limit, so the Owner can see how close the system is to pausing before it happens.

## 5. Candidate-Facing Screens

### 5.1 Application Form
- Mobile-first, short and clear.
- Language selector at the top (English / हिंदी / मराठी).
- Brief, plain-language notice: "Your application may be reviewed by AI, and if shortlisted, your first interview will be conducted by an AI interviewer over video call. A recruiter reviews every decision."

### 5.2 Interview Invitation (Email)
- Clear structure: date, time, format (video call), expected duration, and a short etiquette note (quiet space, camera on, ID handy, join 5 minutes early).
- One-tap "Confirm this slot" / "Request another time" action.
- Delivered in the candidate's selected language.

### 5.3 Pre-Interview Reminder
- Sent shortly before the scheduled time via Email with the join link.
- Short reassurance line: "This will be a friendly conversation about your background and the role — no trick questions."

### 5.4 Live AI Interview Interface (within Zoom/Meet)
- Bot joins with a clear name/label (e.g., "AI Interviewer — [Company Name]") and a short spoken intro disclosing it's AI and that the session is recorded.
- Natural pacing; the AI should acknowledge answers before moving on, not machine-gun questions.
- Candidate can ask to switch language mid-interview if more comfortable ("You can also answer in Hindi or Marathi any time").

### 5.5 Outcome Notification
- Warm, specific tone regardless of outcome.
- Rejections avoid generic filler; where possible include one genuine, specific point drawn from the scorecard.

## 6. Visual Design Direction

- **Owner Console:** Clean, conversational-first UI — think a hybrid of a chat assistant and a lightweight ATS. Generous whitespace, calm color palette, clear status chips (posted / awaiting responses / interviewing / decided).
- **Candidate Screens:** Warm, approachable, reassuring — rounded UI elements, friendly microcopy, larger mobile-first type.
- **Typography:** Clear sans-serif (e.g., Inter) across both; ensure the font renders Devanagari (Hindi/Marathi) cleanly wherever candidate-facing text appears in those languages.
- **Color coding:** Status colors (green/amber/red) always paired with text labels, never color alone.

## 7. Tone of Voice

- Owner-facing: efficient, assistant-like, confident ("5 responses in — ready to send interview invites?").
- Candidate-facing: warm, transparent, never falsely enthusiastic; especially important given the AI-conducted interview is a novel experience for many candidates.

## 8. Deliverables for Design Phase

- Wireframes: Requirement Intake (chat), Form Preview/Approval, Pipeline List, Scorecard Review.
- High-fidelity mockups (Figma) for both Owner Console and candidate screens, desktop + mobile.
- Interactive prototype specifically for the **live AI interview experience** — highest-novelty touchpoint, needs the most usability testing with real candidates across all three languages.
- Localization review pass for Hindi/Marathi copy (not machine-translated only — native-speaker review recommended).
