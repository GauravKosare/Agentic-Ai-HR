"""
Quota Guard — TRD §3.1a pause-and-notify flow.

The LLM Router raises AIQuotaExhausted and explicitly leaves the response to
the caller: "the caller is responsible for setting the system-wide ai_paused
flag, sending the Owner one reminder Email, and clearing the flag once
resume_at has passed." This module is that caller-side responsibility,
implemented once, so every future agent/endpoint calls the same two functions
instead of each reinventing (or forgetting) this handling.

Design choice — no dedicated "state" table. 06-Backend-Schema.md has no
system_status table, only audit_log with actions 'ai_quota_paused' /
'ai_quota_resumed'. Rather than add a migration for a flag that's really just
a derived fact, `is_ai_paused()` reads the most recent one of those two rows
and checks whether its recorded `resume_at` is still in the future — the flag
is computed, not stored. This also means there's no scheduler needed to
"clear" it at the right moment: the first caller to check after resume_at has
passed both sees "not paused" and lazily logs the resume event itself, so the
audit trail stays complete without any cron/background job existing in this
project.

"One reminder" enforcement: `record_and_notify` checks `is_ai_paused()` first.
If we're already in a logged, not-yet-expired pause window, it does nothing —
no second audit_log row, no second Owner email — even though every LLM call
made during that window will independently hit AIQuotaExhausted and call this
function. Without that check, a busy period would spam one email per failed
call instead of the one TRD actually asks for.
"""

from __future__ import annotations

import datetime as dt
import uuid

from app.connectors import email as email_connector
from app.connectors.llm_router import AIQuotaExhausted
from app.connectors.supabase_client import get_service_client

_PAUSE_ACTION = "ai_quota_paused"
_RESUME_ACTION = "ai_quota_resumed"
_ENTITY_TYPE = "system"
# audit_log.entity_id is UUID NOT NULL, but a quota-pause event isn't about
# any specific row — the nil UUID is a fixed sentinel for "system-level, no
# single entity", not a real record's id.
_SYSTEM_ENTITY_ID = str(uuid.UUID(int=0))


def is_ai_paused() -> tuple[bool, dt.datetime | None]:
    """
    Returns (paused, resume_at). Derived from the latest ai_quota_paused/
    ai_quota_resumed row in audit_log, per the module docstring. Call this
    before attempting an LLM-dependent action to short-circuit a call that's
    certain to fail while paused, rather than walking the whole Gemini+Groq
    chain again just to get the same AIQuotaExhausted.
    """
    client = get_service_client()
    response = (
        client.table("audit_log")
        .select("action, details, created_at")
        .eq("entity_type", _ENTITY_TYPE)
        .in_("action", [_PAUSE_ACTION, _RESUME_ACTION])
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    if not rows or rows[0]["action"] == _RESUME_ACTION:
        return False, None

    resume_at = dt.datetime.fromisoformat(rows[0]["details"]["resume_at"])
    if dt.datetime.now(dt.timezone.utc) >= resume_at:
        _log_resume(resume_at)
        return False, None

    return True, resume_at


def record_and_notify(exc: AIQuotaExhausted) -> None:
    """
    Call this from an `except AIQuotaExhausted as exc:` block anywhere an
    agent calls the LLM Router. Logs the pause to audit_log and best-effort
    emails every active Owner one reminder — but only once per pause window
    (see module docstring). Does NOT re-raise: this function's job is the
    side effect (log + notify), not deciding how the caller's own request
    should fail — that stays the caller's responsibility (e.g. an API
    endpoint turning this into a 503).
    """
    already_paused, _ = is_ai_paused()
    if already_paused:
        return

    _log_pause(exc)
    _notify_owners(exc)


def _log_pause(exc: AIQuotaExhausted) -> None:
    get_service_client().table("audit_log").insert({
        "entity_type": _ENTITY_TYPE,
        "entity_id": _SYSTEM_ENTITY_ID,
        "action": _PAUSE_ACTION,
        "actor_type": "system",
        "details": {"resume_at": exc.resume_at.isoformat(), "detail": exc.detail},
    }).execute()


def _log_resume(resume_at: dt.datetime) -> None:
    get_service_client().table("audit_log").insert({
        "entity_type": _ENTITY_TYPE,
        "entity_id": _SYSTEM_ENTITY_ID,
        "action": _RESUME_ACTION,
        "actor_type": "system",
        "details": {"resume_at": resume_at.isoformat()},
    }).execute()


def _notify_owners(exc: AIQuotaExhausted) -> None:
    """
    Best-effort. A failed notification email must never mask the original
    quota exhaustion from the caller — record_and_notify doesn't raise either
    way, but if it did, an email failure here still shouldn't be what the
    caller sees, so failures are swallowed after the pause is already logged
    above. Queries `owners` directly (not hardcoded to one address) since the
    schema supports multiple Owner accounts even though this MVP typically
    has zero or one — no owners existing yet (no signup flow built) is a
    normal, not-an-error case, not something to crash on.
    """
    try:
        owners = get_service_client().table("owners").select("email, full_name").eq("is_active", True).execute().data or []
    except Exception:  # noqa: BLE001 — best-effort, see docstring
        owners = []

    subject = "AI Recruiter Agent — automated processing paused (free quota reached)"
    html = (
        f"<p>Today's free-tier AI request quota (Gemini + Groq) has been used up.</p>"
        f"<p><strong>Detail:</strong> {exc.detail}</p>"
        f"<p>Processing will resume automatically once the quota resets, expected around "
        f"<strong>{exc.resume_at.isoformat()}</strong> — no action is needed on your part. "
        f"This is the only reminder you'll get for this pause window.</p>"
    )

    for owner in owners:
        try:
            email_connector.send_plain_email(
                to_email=owner["email"],
                subject=subject,
                html_content=html,
                to_name=owner.get("full_name"),
            )
        except Exception:  # noqa: BLE001 — best-effort, see docstring; the pause itself is already logged
            continue
