"""
Tests for the FastAPI app's routing/status-code/error-shape behavior. The
Requirement Parser and quota guard are both mocked here — the agent's own
logic is covered in test_requirement_parser.py, the guard's in
test_quota_guard.py. This file only checks that main.py wires them together
correctly.
"""

import datetime as dt
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.agents.requirement_parser import RequirementParsingError, RequisitionDraft
from app.connectors.llm_router import AIQuotaExhausted
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_parse_requisition_success():
    draft = RequisitionDraft(role_title="Backend Intern", quantity=2, work_mode="remote")
    with (
        patch("app.main.quota_guard.is_ai_paused", return_value=(False, None)),
        patch("app.main.parse_requirement", return_value=draft),
    ):
        response = client.post("/requisitions/parse", json={"raw_brief_text": "2 backend interns, remote"})
    assert response.status_code == 200
    assert response.json()["role_title"] == "Backend Intern"


def test_parse_requisition_short_circuits_when_already_paused():
    resume_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1)
    with (
        patch("app.main.quota_guard.is_ai_paused", return_value=(True, resume_at)),
        patch("app.main.parse_requirement") as mock_parse,
    ):
        response = client.post("/requisitions/parse", json={"raw_brief_text": "anything"})
    assert response.status_code == 503
    assert response.json()["detail"]["error"] == "ai_paused"
    mock_parse.assert_not_called()  # the whole point of checking is_ai_paused first


def test_parse_requisition_handles_quota_exhaustion_mid_call():
    exc = AIQuotaExhausted(resume_at=dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1), detail="both exhausted")
    with (
        patch("app.main.quota_guard.is_ai_paused", return_value=(False, None)),
        patch("app.main.parse_requirement", side_effect=exc),
        patch("app.main.quota_guard.record_and_notify") as mock_notify,
    ):
        response = client.post("/requisitions/parse", json={"raw_brief_text": "anything"})
    assert response.status_code == 503
    assert response.json()["detail"]["error"] == "ai_paused"
    mock_notify.assert_called_once()


def test_parse_requisition_handles_parsing_error():
    exc = RequirementParsingError("bad json", "raw text")
    with (
        patch("app.main.quota_guard.is_ai_paused", return_value=(False, None)),
        patch("app.main.parse_requirement", side_effect=exc),
    ):
        response = client.post("/requisitions/parse", json={"raw_brief_text": "garbled"})
    assert response.status_code == 422
    assert response.json()["detail"]["error"] == "parsing_failed"
