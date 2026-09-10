"""
FastAPI entry point.

Auth: every Owner-facing endpoint depends on `get_current_owner` (app/core/auth.py)
— a verified Supabase JWT at `aal2` (password + TOTP MFA), resolved to an
`owners` row. `/health`, `/system/ai-status`, and CORS preflight are the only
unauthenticated routes. Candidate-facing endpoints (tokenized links, no login)
come later and will have their own token scheme, not this dependency.

Agent endpoints (POST /requisitions/parse, POST /forms/build) share `_run_agent_call`:
check quota_guard.is_ai_paused() first, catch AIQuotaExhausted and the agent's
own domain error distinctly, return typed error bodies not a raw 500.

Run with (from src/backend, venv activated):
    uvicorn app.main:app --reload
"""

from __future__ import annotations

import datetime as dt
from typing import Callable, TypeVar

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.agents.form_builder import FormBuildError, FormSchema, build_form
from app.agents.requirement_parser import RequirementParsingError, RequisitionDraft, parse_requirement
from app.connectors.llm_router import AIQuotaExhausted
from app.connectors.supabase_client import get_service_client
from app.core import quota_guard
from app.core.auth import Owner, get_current_owner
from app.core.config import get_settings

app = FastAPI(title="AI Recruiter Agent Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().frontend_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

T = TypeVar("T")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/system/ai-status")
def ai_status() -> dict:
    """Powers the Owner Console's AI status chip (UI-UX §4.3a). No side effects, safe to poll."""
    paused, resume_at = quota_guard.is_ai_paused()
    return {"paused": paused, "resume_at": resume_at.isoformat() if resume_at else None}


@app.post("/auth/session", response_model=Owner)
def announce_session(owner: Owner = Depends(get_current_owner)) -> Owner:
    """
    The frontend calls this once immediately after a successful login reaches
    aal2. It's the point where the backend learns a login happened (login itself
    is Supabase-side), so it writes the one `owner_login` audit row here rather
    than on every subsequent request. Returns the Owner profile for the console
    to display.
    """
    get_service_client().table("audit_log").insert({
        "entity_type": "owner",
        "entity_id": owner.owner_id,
        "action": "owner_login",
        "actor_type": "owner",
        "actor_id": owner.owner_id,
        "details": {"email": owner.email, "at": dt.datetime.now(dt.timezone.utc).isoformat()},
    }).execute()
    return owner


def _run_agent_call(fn: Callable[[], T], domain_error_type: type[Exception], domain_error_label: str) -> T:
    """
    Shared shape for every agent endpoint. `domain_error_type` is each agent's
    own "the model's output couldn't be turned into a valid result" exception —
    always mapped to 422. AIQuotaExhausted is handled once, here: log+notify via
    quota_guard, then 503.
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
def parse_requisition(
    body: ParseRequirementBody,
    owner: Owner = Depends(get_current_owner),
) -> RequisitionDraft:
    # `owner` is required for authorization; the parsed draft isn't persisted
    # yet (no requisitions-table write exists — that step attaches owner.owner_id
    # when it's built).
    return _run_agent_call(
        lambda: parse_requirement(body.raw_brief_text),
        domain_error_type=RequirementParsingError,
        domain_error_label="parsing_failed",
    )


@app.post("/forms/build", response_model=FormSchema)
def build_form_endpoint(
    requisition: RequisitionDraft,
    owner: Owner = Depends(get_current_owner),
) -> FormSchema:
    """
    Takes a RequisitionDraft body, not raw text — TRD §3.2's flow is
    requisition -> form as its own step, after the Owner has reviewed/edited
    whatever /requisitions/parse produced.
    """
    return _run_agent_call(
        lambda: build_form(requisition),
        domain_error_type=FormBuildError,
        domain_error_label="form_build_failed",
    )
