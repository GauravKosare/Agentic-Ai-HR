# Frontend — Owner Console

React + TypeScript + Vite + Tailwind (v4). The recruiter-facing web app
(TRD §2, UI-UX §4). Candidate-facing screens (§5) come later.

## What's here so far (Phase 1)

- **Requirement Intake** (UI-UX §4.1) — plain-language brief → `POST /requisitions/parse` → editable structured summary.
- **Form Preview & Approval** (§4.2) — editable requisition → `POST /forms/build` → read-only preview of the candidate form exactly as it'll appear.
- **AI status chip** (§4.3a) — polls `GET /system/ai-status`; shows when the LLM Router is paused on free-tier quota (TRD §3.1a) and when it resumes.

**Not yet:** auth (the backend has none either — same "build the flows first" order), per-field inline form editing, and anything past "Approve" (distribution is Phase 2).

## Run it

The backend must be running first — from `src/backend` with the venv active:

```bash
uvicorn app.main:app --reload    # serves on http://localhost:8000
```

Then, from `src/frontend`:

```bash
npm install
npm run dev                       # serves on http://localhost:5173
```

Vite proxies `/api/*` to the backend (`vite.config.ts`), so no CORS setup is
needed in dev. For a deployed build, set `VITE_API_BASE_URL` — see `.env.example`.

## Layout

```
src/
├── api.ts              ← typed fetch client; ApiError.paused flags the 503 ai_paused case
├── types.ts             ← mirrors the backend Pydantic models — change both in one commit
├── App.tsx               ← two-step flow: intake → review, requisition state lives here
└── components/
    ├── RequirementIntake.tsx   ← the chat-style brief input (§4.1)
    ├── RequisitionCard.tsx      ← editable structured summary — the source of truth (TRD Stage 1)
    ├── FormPreview.tsx           ← read-only candidate-form preview (§4.2)
    └── AiStatusChip.tsx           ← the §4.3a status indicator
```
