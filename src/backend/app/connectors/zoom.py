"""
Zoom connector (Server-to-Server OAuth) — TRD §3.6.

Uses a Server-to-Server OAuth app (marketplace.zoom.us -> Develop -> Build App),
not the retired JWT app type — this lets the backend create meetings without any
per-request user login/consent step, which is what an automated bot needs.

Free-tier constraint (TRD §3.6): a Zoom Basic account caps every meeting at 40
minutes, including 1:1 calls. Our default interview_time_limit_minutes is 30
(06-Backend-Schema.md), comfortably under that — this connector does not enforce
the cap itself, but callers should not pass a duration above 40 without first
confirming the account has been upgraded.
"""

from __future__ import annotations

import base64
import time
from dataclasses import dataclass

import httpx

from app.core.config import get_settings

ZOOM_OAUTH_URL = "https://zoom.us/oauth/token"
ZOOM_API_BASE = "https://api.zoom.us/v2"

_token_cache: dict[str, tuple[str, float]] = {}


@dataclass
class ZoomMeeting:
    meeting_id: str
    join_url: str
    start_url: str


class ZoomAPIError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Zoom API error ({status_code}): {detail}")


def _get_access_token() -> str:
    """Server-to-Server OAuth token, cached in-process until shortly before it expires (tokens last 1 hour)."""
    settings = get_settings()
    settings.require("zoom_account_id", "zoom_client_id", "zoom_client_secret")

    cached = _token_cache.get("token")
    if cached and cached[1] > time.time() + 60:
        return cached[0]

    credentials = base64.b64encode(f"{settings.zoom_client_id}:{settings.zoom_client_secret}".encode()).decode()
    response = httpx.post(
        ZOOM_OAUTH_URL,
        headers={"Authorization": f"Basic {credentials}"},
        params={"grant_type": "account_credentials", "account_id": settings.zoom_account_id},
        timeout=10,
    )
    if response.status_code >= 300:
        raise ZoomAPIError(response.status_code, response.text)

    body = response.json()
    token = body["access_token"]
    expires_in = body.get("expires_in", 3600)
    _token_cache["token"] = (token, time.time() + expires_in)
    return token


def create_instant_meeting(topic: str, duration_minutes: int = 30) -> ZoomMeeting:
    """
    Creates a Zoom meeting for the Meeting Orchestration Agent (TRD §3.6). type=1
    (instant) starts immediately; for interviews scheduled ahead of time, TRD's
    design calls the meeting-creation step "at the scheduled time" rather than far
    in advance, so instant-meeting semantics fit the intended flow.
    """
    token = _get_access_token()
    response = httpx.post(
        f"{ZOOM_API_BASE}/users/me/meetings",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "topic": topic,
            "type": 1,  # instant meeting
            "settings": {
                "join_before_host": True,
                "waiting_room": False,
            },
        },
        timeout=15,
    )
    if response.status_code >= 300:
        raise ZoomAPIError(response.status_code, response.text)

    body = response.json()
    return ZoomMeeting(
        meeting_id=str(body["id"]),
        join_url=body["join_url"],
        start_url=body["start_url"],
    )


def health_check() -> tuple[bool, str]:
    """Confirms Server-to-Server OAuth credentials are valid by fetching a token — creates no meeting, costs nothing."""
    try:
        _get_access_token()
        return True, "Zoom reachable, Server-to-Server OAuth credentials valid."
    except Exception as exc:  # noqa: BLE001
        return False, f"Zoom health check failed: {exc}"
