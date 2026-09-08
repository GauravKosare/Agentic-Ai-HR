"""
FastAPI entry point.

Currently exposes one real endpoint (POST /requisitions/parse) — deliberately
just the one, to prove out the calling convention every future agent endpoint
should follow before more get added: check quota_guard.is_ai_paused() first to
short-circuit a call that's certain to fail, catch AIQuotaExhausted and the
agent's own parsing-failure exception distinctly, return typed error bodies
rather than a raw 500. More endpoints get added agent-by-agent as Phase 1
continues (05-Implementation-Plan.md).

Run with (from src/backend, venv activated):
    uvicorn app.main:app --reload
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.agents.requirement_parser import RequirementParsingError, RequisitionDraft, parse_requirement
from app.connectors.llm_router import AIQuotaExhausted
from app.core import quota_guard

app = FastAPI(title="AI Recruiter Agent Backend")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


class ParseRequirementBody(BaseModel):
    raw_brief_text: str


@app.post("/requisitions/parse", response_model=RequisitionDraft)
def parse_requisition(body: ParseRequirementBody) -> RequisitionDraft:
    paused, resume_at = quota_guard.is_ai_paused()
    if paused:
        raise HTTPException(
            status_code=503,
            detail={"error": "ai_paused", "resume_at": resume_at.isoformat() if resume_at else None},
        )

    try:
        return parse_requirement(body.raw_brief_text)
    except AIQuotaExhausted as exc:
        quota_guard.record_and_notify(exc)
        raise HTTPException(
            status_code=503,
            detail={"error": "ai_paused", "resume_at": exc.resume_at.isoformat(), "detail": exc.detail},
        ) from exc
    except RequirementParsingError as exc:
        raise HTTPException(status_code=422, detail={"error": "parsing_failed", "detail": exc.detail}) from exc
