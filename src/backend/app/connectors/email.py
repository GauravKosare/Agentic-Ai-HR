"""
Email connector (Brevo) — TRD §3.5.

The sole candidate messaging channel (WhatsApp was deliberately excluded — see
07-Financial-Subscription-Tracking.md). Uses Brevo's transactional email API
directly (not the SMTP relay) so we can send by template ID with params, matching
the "Interview Invitation" template created in the Brevo dashboard.

Free tier: 300 sends/day, permanent. No fallback provider — if the daily cap is
hit, TRD §8 says to flag for Owner review and retry once after a delay, not to
silently drop the message or reach for a paid channel.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.core.config import get_settings

BREVO_API_BASE = "https://api.brevo.com/v3"


@dataclass
class EmailResult:
    message_id: str


class EmailSendFailed(Exception):
    """Raised on any non-2xx response from Brevo — e.g. daily cap reached (401/402-style
    quota errors), invalid template, invalid recipient. Callers should flag for Owner
    review and retry once after a delay (TRD §8), not silently drop the message."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Brevo send failed ({status_code}): {detail}")


def send_template_email(
    to_email: str,
    template_id: int,
    params: dict,
    to_name: str | None = None,
) -> EmailResult:
    """
    Send a transactional email via a Brevo template (e.g. the Interview Invitation
    template, TRD §3.5 — date/time/format/duration/etiquette note). `params` fills
    the template's {{params.*}} placeholders; `to_name` fills {{contact.FNAME}}-style
    fields if the template uses them.
    """
    settings = get_settings()
    settings.require("brevo_api_key")

    payload = {
        "to": [{"email": to_email, "name": to_name} if to_name else {"email": to_email}],
        "templateId": template_id,
        "params": params,
    }

    response = httpx.post(
        f"{BREVO_API_BASE}/smtp/email",
        headers={"api-key": settings.brevo_api_key, "content-type": "application/json"},
        json=payload,
        timeout=15,
    )
    if response.status_code >= 300:
        raise EmailSendFailed(response.status_code, response.text)

    return EmailResult(message_id=response.json().get("messageId", ""))


def health_check() -> tuple[bool, str]:
    """Confirms the API key is valid by reading account info — makes no send, costs nothing against the daily cap."""
    settings = get_settings()
    try:
        settings.require("brevo_api_key")
        response = httpx.get(
            f"{BREVO_API_BASE}/account",
            headers={"api-key": settings.brevo_api_key},
            timeout=10,
        )
        if response.status_code >= 300:
            return False, f"Brevo account check failed ({response.status_code}): {response.text}"
        plan = response.json().get("plan", [{}])
        credits = plan[0].get("credits") if plan else "unknown"
        return True, f"Brevo reachable, key valid. Plan credits: {credits}"
    except Exception as exc:  # noqa: BLE001
        return False, f"Email health check failed: {exc}"
