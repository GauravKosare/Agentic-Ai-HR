"""
Unit tests for the Form Builder Agent. The LLM call is mocked throughout —
these test the baseline/dynamic-field merge and validation logic, not
Gemini/Groq's actual output. A real smoke test against live credentials
belongs in scripts/, not here.
"""

import json
from unittest.mock import patch

import pytest

from app.agents.form_builder import (
    AI_DISCLOSURE_NOTICE,
    FormBuildError,
    FormField,
    build_form,
)
from app.agents.requirement_parser import RequisitionDraft
from app.connectors.llm_router import LLMResult, Task


def _fake_result(payload: dict) -> LLMResult:
    return LLMResult(text=json.dumps(payload), provider="gemini", model="test-model", task=Task.FORM_GENERATION)


def _requisition(**overrides) -> RequisitionDraft:
    defaults = dict(role_title="Backend Development Intern", quantity=3, work_mode="remote")
    defaults.update(overrides)
    return RequisitionDraft(**defaults)


def test_build_form_skips_llm_call_when_nothing_role_specific():
    requisition = _requisition(required_skills=[], eligibility_rules={})
    with patch("app.agents.form_builder.generate") as mock_gen:
        form = build_form(requisition)
    mock_gen.assert_not_called()
    # baseline-only: exactly the 7 hardcoded fields, nothing extra
    assert len(form.fields) == 7


def test_build_form_always_includes_the_exact_disclosure_notice():
    requisition = _requisition(required_skills=[], eligibility_rules={})
    with patch("app.agents.form_builder.generate"):
        form = build_form(requisition)
    notice_field = next(f for f in form.fields if f.field_id == "ai_disclosure_notice")
    assert notice_field.label == AI_DISCLOSURE_NOTICE


def test_build_form_calls_llm_and_merges_dynamic_fields_when_skills_present():
    requisition = _requisition(required_skills=["Python", "SQL"])
    dynamic_payload = {
        "fields": [
            {"field_id": "skill_python", "label": "How would you rate your Python skills?", "field_type": "select",
             "required": True, "options": ["Beginner", "Intermediate", "Advanced"], "help_text": None},
            {"field_id": "skill_sql", "label": "How would you rate your SQL skills?", "field_type": "select",
             "required": True, "options": ["Beginner", "Intermediate", "Advanced"], "help_text": None},
        ]
    }
    with patch("app.agents.form_builder.generate", return_value=_fake_result(dynamic_payload)) as mock_gen:
        form = build_form(requisition)

    mock_gen.assert_called_once()
    assert mock_gen.call_args.kwargs["task"] == Task.FORM_GENERATION
    field_ids = {f.field_id for f in form.fields}
    assert {"skill_python", "skill_sql"}.issubset(field_ids)
    assert len(form.fields) == 9  # 7 baseline + 2 dynamic


def test_build_form_raises_on_field_id_collision_with_baseline():
    requisition = _requisition(required_skills=["Email writing"])
    colliding_payload = {"fields": [{"field_id": "email", "label": "Rate your email skills", "field_type": "text",
                                      "required": True, "options": None, "help_text": None}]}
    with patch("app.agents.form_builder.generate", return_value=_fake_result(colliding_payload)):
        with pytest.raises(FormBuildError):
            build_form(requisition)


def test_build_form_raises_on_invalid_json_from_llm():
    requisition = _requisition(required_skills=["Python"])
    bad_result = LLMResult(text="not json", provider="gemini", model="test-model", task=Task.FORM_GENERATION)
    with patch("app.agents.form_builder.generate", return_value=bad_result):
        with pytest.raises(FormBuildError):
            build_form(requisition)


def test_build_form_raises_on_schema_mismatch_from_llm():
    requisition = _requisition(required_skills=["Python"])
    malformed = {"fields": [{"field_id": "x", "label": "y", "field_type": "not-a-real-type"}]}
    with patch("app.agents.form_builder.generate", return_value=_fake_result(malformed)):
        with pytest.raises(FormBuildError):
            build_form(requisition)


def test_form_field_defaults_to_required_true():
    field = FormField(field_id="x", label="X", field_type="text")
    assert field.required is True
