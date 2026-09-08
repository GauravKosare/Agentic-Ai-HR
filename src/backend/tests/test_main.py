"""
Tests for the FastAPI app's routing/status-code/error-shape behavior. The
agents and quota guard are all mocked here — each agent's own logic is
covered in its own test file (test_requirement_parser.py,
test_form_builder.py), the guard's in test_quota_guard.py. This file only
checks that main.py wires them together correctly.
"""

import datetime as dt
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.agents.form_builder import FormBuildError, FormField, FormSchema
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


_REQUISITION_BODY = {"role_title": "Backend Intern", "quantity": 2, "work_mode": "remote"}


def test_build_form_success():
    form = FormSchema(fields=[FormField(field_id="full_name", label="Full name", field_type="text")])
    with (
        patch("app.main.quota_guard.is_ai_paused", return_value=(False, None)),
        patch("app.main.build_form", return_value=form),
    ):
        response = client.post("/forms/build", json=_REQUISITION_BODY)
    assert response.status_code == 200
    assert response.json()["fields"][0]["field_id"] == "full_name"


def test_build_form_short_circuits_when_already_paused():
    resume_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1)
    with (
        patch("app.main.quota_guard.is_ai_paused", return_value=(True, resume_at)),
        patch("app.main.build_form") as mock_build,
    ):
        response = client.post("/forms/build", json=_REQUISITION_BODY)
    assert response.status_code == 503
    mock_build.assert_not_called()


def test_build_form_handles_quota_exhaustion_mid_call():
    exc = AIQuotaExhausted(resume_at=dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1), detail="both exhausted")
    with (
        patch("app.main.quota_guard.is_ai_paused", return_value=(False, None)),
        patch("app.main.build_form", side_effect=exc),
        patch("app.main.quota_guard.record_and_notify") as mock_notify,
    ):
        response = client.post("/forms/build", json=_REQUISITION_BODY)
    assert response.status_code == 503
    mock_notify.assert_called_once()


def test_build_form_handles_form_build_error():
    exc = FormBuildError("bad json", "raw text")
    with (
        patch("app.main.quota_guard.is_ai_paused", return_value=(False, None)),
        patch("app.main.build_form", side_effect=exc),
    ):
        response = client.post("/forms/build", json=_REQUISITION_BODY)
    assert response.status_code == 422
    assert response.json()["detail"]["error"] == "form_build_failed"


def test_build_form_rejects_invalid_requisition_body():
    # work_mode null with no clarifying_question is invalid per
    # RequisitionDraft's own validator — FastAPI should reject this at the
    # request-validation layer (422) before build_form is ever called.
    with patch("app.main.build_form") as mock_build:
        response = client.post("/forms/build", json={"role_title": "X", "quantity": 1, "work_mode": None})
    assert response.status_code == 422
    mock_build.assert_not_called()
