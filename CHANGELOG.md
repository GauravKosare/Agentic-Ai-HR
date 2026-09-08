# Changelog

All notable changes to this project will be documented in this file.

## [0.6.1] — 2026-09-08 — Phase 0 Complete

All 5 foundation connectors (Supabase, LLM Router, Speech-to-Text, Email, Zoom) confirmed healthy end-to-end against real credentials via `scripts/check_connectors.py`. Phase 0 of [05-Implementation-Plan.md](docs/05-Implementation-Plan.md) is done; next is Phase 1 (Requirement Parser Agent, Form Builder Agent).

## [0.6.0] — 2026-09-08 — Email and Zoom Connectors, Supabase Restore

### Added
- `app/connectors/email.py` — Brevo transactional email (TRD §3.5), confirmed working against a real key.
- `app/connectors/zoom.py` — Zoom Server-to-Server OAuth (TRD §3.6): token fetch/cache, instant meeting creation.
- Tests for the Zoom token-cache freshness logic.

### Fixed
- The Supabase project had auto-paused after being idle since July 19 (Supabase free tier pauses after 1 week inactive — exactly the risk documented in the Financial doc) and was surfaced as a DNS resolution failure, not an obvious "paused" message. Restored via the Supabase MCP connector. Documented the symptom and fix in `src/backend/README.md` so it's recognizable next time.

## [0.5.0] — 2026-07-20 — Supabase Schema Live, Brevo Configured, Browser-Native Meeting Bot

### Added
- Applied the full database schema (17 tables, RLS on every owner-traceable table, 2 private storage buckets, Realtime on `applications`) to the live Supabase project via 6 migrations.
- Configured Brevo: confirmed free-tier account (300 sends/day) and verified sender; created the interview-invitation transactional email template.

### Changed
- **Meeting bot replaced again:** Vexa → a custom, self-hosted **Playwright/Chromium bot** that joins Zoom/Meet via their browser web-join URLs. Needed because Chrome's Web Speech APIs only run inside a live browser tab, not via a headless audio-stream service like Vexa provided.
- **STT/TTS primary switched to Chrome's built-in `SpeechRecognition`/`speechSynthesis`**, running in that same browser tab — free, no API key, no metering. The previously-built Groq-hosted Whisper chain and self-hosted AI4Bharat TTS are kept as fallbacks, not discarded.
- Meeting creation (Zoom/Google Meet APIs) is unchanged — only the join/audio mechanism changed.
- New documented risks: an unbuilt, unproven OS-level virtual-audio-routing requirement (flagged as the single highest-uncertainty item in the project), and unvalidated Chrome `speechSynthesis` voice quality for Hindi/Marathi on a headless Linux host.
- Updated TRD, PRD, Workflow, Implementation Plan, README, LICENSE, and the Financial & Subscription Tracking doc (§4b) accordingly.

## [0.4.0] — 2026-07-20 — Backend Connector Scaffold, Multi-Model Chains, Groq-Hosted STT

### Added
- `src/backend/` — first application code: Supabase connector, LLM Router connector, Speech-to-Text connector, config, tests, `.env.example`, and a `check_connectors.py` script that verifies each connector against real credentials without ever printing secret values.

### Changed
- **LLM Router redesigned as per-provider, per-tier model CHAINS**, not single models: Gemini tries `gemini-3.5-flash` → `gemini-3-flash` (reasoning) or `gemini-3.1-flash-lite` → `gemma-4-26b` → `gemma-4-31b` (light) before falling to Groq's chain (`openai/gpt-oss-120b` → `llama-3.3-70b-versatile` → `qwen/qwen3.6-27b` reasoning; `openai/gpt-oss-20b` → `llama-3.1-8b-instant` light). Only pauses once every model in both chains is exhausted. Model choices sourced from live account quota data, not vendor docs.
- **Task-specific routing implemented**: a `Task` enum (one per named TRD/Workflow agent) maps to a tier in one place (`TASK_TIER`), so every LLM call site is explicit about which agent it's acting as.
- **STT moved from self-hosted Whisper to Groq-hosted Whisper** (`whisper-large-v3-turbo` → `whisper-large-v3` chain) — LPU-accelerated, free, resolves the CPU-only latency risk directly. Documented and accepted trade-off: this makes Groq a second dependency alongside the LLM Router fallback, so a Groq outage affects both at once (correlated, not independent) — see 07-Financial-Subscription-Tracking.md §4a/§5.
- Corrected a real credential mix-up (an xAI/Grok key was mistakenly used as the Groq key — different company, no free tier) and multiple stale model names (Groq deprecated `llama-3.3-70b-versatile`/`llama-3.1-8b-instant` on the free tier 2026-06-17; Gemini shut down 2.0 and stopped offering 2.5-flash-lite to new users) — all caught via live testing against real accounts, not assumed.
- Switched Supabase to its new key format (`sb_secret_...`/`sb_publishable_...`) instead of the legacy `service_role`/`anon` JWTs, which are being deprecated by end of 2026.
- Updated TRD, PRD, Workflow, Implementation Plan, README, and the Financial & Subscription Tracking doc to match.

## [0.3.1] — 2026-07-19 — Voice Pipeline Hosting: Oracle Cloud Always Free VM

### Changed
- Hosting for the Vexa + Whisper + AI4Bharat voice/meeting-bot pipeline moved from "Cloud Run free tier" to an **Oracle Cloud Always Free ARM VM** (currently 2 OCPU/12GB RAM, permanent — not a trial). This is a long-running, stateful process for the duration of each interview, which doesn't fit a serverless request/response platform architecturally, independent of cost. Cloud Run/Render remain correct for the stateless backend API paths (requirement parsing, form, distribution, notifications, scoring).
- Documented that GPU is never free on any mainstream cloud, so the speech pipeline runs CPU-only via a quantized Whisper "small" model (faster-whisper, int8), with realistic latency of ~0.5–2s rather than the ~1s ideal target.
- Flagged that Oracle silently cut its Always Free VM allocation in June 2026 (4 OCPU/24GB → 2 OCPU/12GB) with no announcement — noted as a live example of the free-tier-terms-drift risk already tracked in the Financial doc.
- Updated TRD, Implementation Plan, Financial & Subscription Tracking, Workflow, PRD, and README accordingly.

## [0.3.0] — 2026-07-19 — Zero-Cost Stack: Gemini/Groq LLM Router, Self-Hosted Speech & Meeting Bot, Email-Only

### Changed
- **LLM:** Claude Sonnet 5 replaced with a Gemini API (free tier, primary) → Groq API (free tier, fallback) router. On exhaustion of both free tiers, the system pauses all AI-dependent actions, sends the Owner one reminder notification, and resumes automatically at the next quota reset rather than ever calling a paid model.
- **Speech (STT/TTS):** Sarvam AI replaced with self-hosted open-source Whisper (STT) and AI4Bharat Indic Parler-TTS/IndicF5 (TTS). Accepted trade-off: weaker Hindi/Marathi code-switching accuracy than the purpose-built commercial option; requires dedicated validation in Phase 5.
- **Meeting bot:** Recall.ai/MeetStream.ai replaced with self-hosted Vexa (open source, Apache 2.0) — no per-minute vendor fee.
- **Candidate messaging:** WhatsApp Business Cloud API removed entirely; Email (via Brevo) is now the sole candidate channel. Meta bills business-initiated template messages with no zero-cost path, so it didn't fit the project's free-tier-only policy.
- **Resume parsing:** now routed through the same Gemini/Groq LLM Router instead of Claude.
- Updated PRD, TRD, Workflow, UI/UX Brief, Implementation Plan, Backend Schema, README, and the Financial & Subscription Tracking document accordingly.

### Rationale
- Project policy shifted to zero recurring cost for the development/pilot stage. Every tool without a genuine free/self-hosted path was either replaced or, where no drop-in replacement existed at comparable quality (the LLM), designed to degrade gracefully instead of incurring cost.

## [0.2.0] — 2026-07-19 — Supabase Migration & Web Application Architecture

### Changed
- Data store, authentication, file storage, and realtime updates consolidated onto **Supabase** (Postgres + pgvector, Auth, Storage, Realtime), replacing the original generic PostgreSQL design.
- Explicit "web application" framing applied throughout: single React SPA serving both the Owner Console and candidate-facing pages, Supabase Auth for Owner login, Row Level Security for single-Owner data isolation.
- Added [07-Financial-Subscription-Tracking.md](./docs/07-Financial-Subscription-Tracking.md) — a living inventory of every tool/service used, free-tier terms, and cost status.
- Replaced Affinda (resume parsing, no permanent free tier) with an LLM-based extraction approach, and SendGrid (free plan discontinued in 2025) with Brevo.

## [0.1.0] — 2026-07-15 — Initial Commit

### Added
- Product Requirements Document (PRD) covering the conversational, agentic hiring assistant vision, scope, functional/non-functional requirements, and compliance posture.
- Technical Requirements Document (TRD) with full system architecture, agent breakdown, and verified technology stack (Claude Sonnet 5, Sarvam AI, Recall.ai/MeetStream.ai, Zoom API, WhatsApp Business Cloud API).
- Workflow documentation with end-to-end process diagram and stage-by-stage breakdown.
- UI/UX Design Brief covering the Owner Console and candidate-facing experience, including multilingual design considerations.
- Implementation Plan with phased roadmap, team structure, milestones, and testing strategy.
- Backend Schema with full PostgreSQL DDL and entity relationship design.
- Proprietary license (all rights reserved).

### Notes
- This is a design/specification-only commit. No application source code is included yet.
- Compliance timelines (EU AI Act, India DPDP Act) and third-party platform API access status were verified as of July 2026 and are documented in the TRD; these should be re-verified periodically as regulations and platform policies evolve.
