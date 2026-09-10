"""
Tests for the FastAPI app's routing/status-code/error-shape/auth wiring. The
agents, quota guard, and the auth dependency are all mocked/overridden here —
each agent's own logic is in its own test file, the guard's in
test_quota_guard.py, the auth dependency's in test_auth.py. This file only
checks that main.py wires them together correctly.
"""

import datetime as dt
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.agents.form_builder import FormBuildError, FormField, FormSchema
from app.agents.requirement_parser import RequirementParsingError, RequisitionDraft
from app.connectors.llm_router import AIQuotaExhausted
from app.core.auth import Owner, get_current_owner
from app.main import app

client = TestClient(app)

_FAKE_OWNER = Owner(
    owner_id="11111111-1111-1111-1111-111111111111",
    auth_user_id="22222222-2222-2222-2222-222222222222",
    email="owner@example.com",
    full_name="Gaurav",
)

_REQUISITION_BODY = {"role_title": "Backend Intern", "quantity": 2, "work_mode": "remote"}


@pytest.fixture
def as_owner():
    """Overrides the auth dependency so an endpoint test runs as a logged-in
    Owner without a real JWT. Cleared after each test."""
    app.dependency_overrides[get_current_owner] = lambda: _FAKE_OWNER
    yield
    app.dependency_overrides.pop(get_current_owner, None)


# --- unauthenticated routes ---

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ai_status_reports_not_paused():
    with patch("app.main.quota_guard.is_ai_paused", return_value=(False, None)):
        response = client.get("/system/ai-status")
    assert response.status_code == 200
    assert response.json() == {"paused": False, "resume_at": None}


def test_ai_status_reports_paused_with_resume_time():
    resume_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1)
    with patch("app.main.quota_guard.is_ai_paused", return_value=(True, resume_at)):
        response = client.get("/system/ai-status")
    assert response.status_code == 200
    body = response.json()
    assert body["paused"] is True and body["resume_at"] == resume_at.isoformat()


# --- auth gate ---

def test_agent_endpoints_require_auth():
    # no dependency override -> real get_current_owner runs -> no header -> 401
    assert client.post("/requisitions/parse", json={"raw_brief_text": "x"}).status_code == 401
    assert client.post("/forms/build", json=_REQUISITION_BODY).status_code == 401
    assert client.post("/auth/session").status_code == 401


def test_auth_session_records_login_and_returns_owner(as_owner):
    with patch("app.main.get_service_client") as mock_client:
        response = client.post("/auth/session")
    assert response.status_code == 200
    assert response.json()["email"] == "owner@example.com"
    # one audit_log insert for the owner_login event
    mock_client.return_value.table.assert_called_with("audit_log")


# --- agent endpoints (authenticated) ---

def test_parse_requisition_success(as_owner):
    draft = RequisitionDraft(role_title="Backend Intern", quantity=2, work_mode="remote")
    with (
        patch("app.main.quota_guard.is_ai_paused", return_value=(False, None)),
        patch("app.main.parse_requirement", return_value=draft),
    ):
        response = client.post("/requisitions/parse", json={"raw_brief_text": "2 backend interns, remote"})
    assert response.status_code == 200
    assert response.json()["role_title"] == "Backend Intern"


def test_parse_requisition_short_circuits_when_already_paused(as_owner):
    resume_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1)
    with (
        patch("app.main.quota_guard.is_ai_paused", return_value=(True, resume_at)),
        patch("app.main.parse_requirement") as mock_parse,
    ):
        response = client.post("/requisitions/parse", json={"raw_brief_text": "anything"})
    assert response.status_code == 503
    assert response.json()["detail"]["error"] == "ai_paused"
    mock_parse.assert_not_called()


def test_parse_requisition_handles_quota_exhaustion_mid_call(as_owner):
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


def test_parse_requisition_handles_parsing_error(as_owner):
    exc = RequirementParsingError("bad json", "raw text")
    with (
        patch("app.main.quota_guard.is_ai_paused", return_value=(False, None)),
        patch("app.main.parse_requirement", side_effect=exc),
    ):
        response = client.post("/requisitions/parse", json={"raw_brief_text": "garbled"})
    assert response.status_code == 422
    assert response.json()["detail"]["error"] == "parsing_failed"


def test_build_form_success(as_owner):
    form = FormSchema(fields=[FormField(field_id="full_name", label="Full name", field_type="text")])
    with (
        patch("app.main.quota_guard.is_ai_paused", return_value=(False, None)),
        patch("app.main.build_form", return_value=form),
    ):
        response = client.post("/forms/build", json=_REQUISITION_BODY)
    assert response.status_code == 200
    assert response.json()["fields"][0]["field_id"] == "full_name"


def test_build_form_short_circuits_when_already_paused(as_owner):
    resume_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1)
    with (
        patch("app.main.quota_guard.is_ai_paused", return_value=(True, resume_at)),
        patch("app.main.build_form") as mock_build,
    ):
        response = client.post("/forms/build", json=_REQUISITION_BODY)
    assert response.status_code == 503
    mock_build.assert_not_called()


def test_build_form_handles_quota_exhaustion_mid_call(as_owner):
    exc = AIQuotaExhausted(resume_at=dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1), detail="both exhausted")
    with (
        patch("app.main.quota_guard.is_ai_paused", return_value=(False, None)),
        patch("app.main.build_form", side_effect=exc),
        patch("app.main.quota_guard.record_and_notify") as mock_notify,
    ):
        response = client.post("/forms/build", json=_REQUISITION_BODY)
    assert response.status_code == 503
    mock_notify.assert_called_once()


def test_build_form_handles_form_build_error(as_owner):
    exc = FormBuildError("bad json", "raw text")
    with (
        patch("app.main.quota_guard.is_ai_paused", return_value=(False, None)),
        patch("app.main.build_form", side_effect=exc),
    ):
        response = client.post("/forms/build", json=_REQUISITION_BODY)
    assert response.status_code == 422
    assert response.json()["detail"]["error"] == "form_build_failed"


def test_build_form_rejects_invalid_requisition_body(as_owner):
    # work_mode null with no clarifying_question is invalid per RequisitionDraft's
    # own validator — FastAPI rejects it at request-validation (422) before build_form.
    with patch("app.main.build_form") as mock_build:
        response = client.post("/forms/build", json={"role_title": "X", "quantity": 1, "work_mode": None})
    assert response.status_code == 422
    mock_build.assert_not_called()
