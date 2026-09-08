"""
FastAPI entry point.

Two agent endpoints so far: POST /requisitions/parse (Requirement Parser) and
POST /forms/build (Form Builder). Both follow the same shape, factored into
`_run_agent_call` below rather than repeated per endpoint: check
quota_guard.is_ai_paused() first to short-circuit a call that's certain to
fail, catch AIQuotaExhausted and the agent's own domain-specific parsing
error distinctly, return typed error bodies rather than a raw 500. More
endpoints get added agent-by-agent as Phase 1 continues
(05-Implementation-Plan.md); the first two proved the pattern, this is where
it stopped being "the endpoint's own logic" and became shared plumbing.

Run with (from src/backend, venv activated):
    uvicorn app.main:app --reload
"""

from __future__ import annotations

from typing import Callable, TypeVar

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.agents.form_builder import FormBuildError, FormSchema, build_form
from app.agents.requirement_parser import RequirementParsingError, RequisitionDraft, parse_requirement
from app.connectors.llm_router import AIQuotaExhausted
from app.core import quota_guard

app = FastAPI(title="AI Recruiter Agent Backend")

T = TypeVar("T")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


def _run_agent_call(fn: Callable[[], T], domain_error_type: type[Exception], domain_error_label: str) -> T:
    """
    Shared shape for every agent endpoint below. `domain_error_type` is each
    agent's own "the model's output couldn't be turned into a valid result"
    exception (e.g. RequirementParsingError, FormBuildError) — always mapped
    to 422, since it means the request itself was fine but the AI-generated
    content wasn't usable. AIQuotaExhausted is handled once, here, the same
    way for every agent: log+notify via quota_guard, then 503 — no endpoint
    needs to know that plumbing exists.
    """
    paused, resume_at = quota_guard.is_ai_paused()
    if paused:
        raise HTTPException(
            status_code=503,
            detail={"error": "ai_paused", "resume_at": resume_at.isoformat() if resume_at else None},
        )

    try:
        return fn()
    except AIQuotaExhausted as exc:
        quota_guard.record_and_notify(exc)
        raise HTTPException(
            status_code=503,
            detail={"error": "ai_paused", "resume_at": exc.resume_at.isoformat(), "detail": exc.detail},
        ) from exc
    except domain_error_type as exc:
        raise HTTPException(status_code=422, detail={"error": domain_error_label, "detail": exc.detail}) from exc


class ParseRequirementBody(BaseModel):
    raw_brief_text: str


@app.post("/requisitions/parse", response_model=RequisitionDraft)
def parse_requisition(body: ParseRequirementBody) -> RequisitionDraft:
    return _run_agent_call(
        lambda: parse_requirement(body.raw_brief_text),
        domain_error_type=RequirementParsingError,
        domain_error_label="parsing_failed",
    )


@app.post("/forms/build", response_model=FormSchema)
def build_form_endpoint(requisition: RequisitionDraft) -> FormSchema:
    """
    Takes a RequisitionDraft body, not raw text — TRD §3.2's flow is
    requisition -> form as its own step, after the Owner has reviewed/edited
    whatever /requisitions/parse produced, not a re-parse of the original brief.
    """
    return _run_agent_call(
        lambda: build_form(requisition),
        domain_error_type=FormBuildError,
        domain_error_label="form_build_failed",
    )
