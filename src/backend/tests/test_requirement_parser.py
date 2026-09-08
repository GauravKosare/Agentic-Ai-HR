"""
Unit tests for the Requirement Parser Agent. The LLM call is mocked throughout —
these test the parsing/validation logic, not Gemini/Groq's actual output. A
real smoke test against live credentials belongs in scripts/, not here.
"""

import json
from unittest.mock import patch

import pytest

from app.agents.requirement_parser import (
    RequirementParsingError,
    RequisitionDraft,
    _extract_json,
    parse_requirement,
)
from app.connectors.llm_router import LLMResult, Task


def _fake_result(payload: dict) -> LLMResult:
    return LLMResult(text=json.dumps(payload), provider="gemini", model="test-model", task=Task.REQUIREMENT_PARSING)


FULL_BRIEF_PAYLOAD = {
    "role_title": "Backend Development Intern",
    "quantity": 3,
    "work_mode": "remote",
    "duration": "3 months",
    "compensation": "₹15,000/month",
    "required_skills": ["Python", "SQL"],
    "eligibility_rules": {"seniority_level": "intern"},
    "clarifying_question": None,
}


def test_extract_json_parses_clean_json():
    assert _extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_strips_markdown_fences():
    fenced = '```json\n{"a": 1}\n```'
    assert _extract_json(fenced) == {"a": 1}


def test_extract_json_raises_on_invalid_json():
    with pytest.raises(RequirementParsingError):
        _extract_json("not json at all")


def test_parse_requirement_returns_full_draft_when_brief_is_clear():
    with patch("app.agents.requirement_parser.generate", return_value=_fake_result(FULL_BRIEF_PAYLOAD)) as mock_gen:
        draft = parse_requirement("3 backend interns, remote, 3 months, ₹15k stipend")

    assert isinstance(draft, RequisitionDraft)
    assert draft.role_title == "Backend Development Intern"
    assert draft.quantity == 3
    assert draft.work_mode == "remote"
    assert draft.required_skills == ["Python", "SQL"]
    assert draft.clarifying_question is None
    mock_gen.assert_called_once()
    assert mock_gen.call_args.kwargs["task"] == Task.REQUIREMENT_PARSING


def test_parse_requirement_carries_a_clarifying_question_alongside_the_draft():
    payload = {**FULL_BRIEF_PAYLOAD, "clarifying_question": "Should this be open to final-year students or only graduates?"}
    with patch("app.agents.requirement_parser.generate", return_value=_fake_result(payload)):
        draft = parse_requirement("hiring backend interns")

    # The draft is still fully usable even though a question was also raised —
    # clarification augments the draft, it doesn't block it (TRD §3.1 / UI-UX §4.1).
    assert draft.role_title == "Backend Development Intern"
    assert draft.clarifying_question is not None


def test_parse_requirement_rejects_empty_brief_without_calling_the_llm():
    with patch("app.agents.requirement_parser.generate") as mock_gen:
        with pytest.raises(RequirementParsingError):
            parse_requirement("   ")
    mock_gen.assert_not_called()


def test_parse_requirement_raises_on_missing_required_field():
    incomplete = {**FULL_BRIEF_PAYLOAD}
    del incomplete["role_title"]
    with patch("app.agents.requirement_parser.generate", return_value=_fake_result(incomplete)):
        with pytest.raises(RequirementParsingError):
            parse_requirement("some brief")


def test_parse_requirement_raises_on_invalid_work_mode():
    bad = {**FULL_BRIEF_PAYLOAD, "work_mode": "fully-remote-but-not-really"}
    with patch("app.agents.requirement_parser.generate", return_value=_fake_result(bad)):
        with pytest.raises(RequirementParsingError):
            parse_requirement("some brief")


def test_quantity_must_be_positive():
    with pytest.raises(Exception):  # noqa: B017 — pydantic ValidationError, checked generically here
        RequisitionDraft(role_title="x", quantity=0, work_mode="remote")


def test_null_work_mode_requires_a_clarifying_question():
    # Caught by a live test against a genuinely ambiguous brief: the model
    # correctly left work_mode null, but without this rule a null work_mode
    # with no explanation would validate silently.
    with pytest.raises(Exception):  # noqa: B017 — pydantic ValidationError
        RequisitionDraft(role_title="Sales Intern", quantity=1, work_mode=None)


def test_null_work_mode_is_fine_with_a_clarifying_question():
    draft = RequisitionDraft(
        role_title="Sales Intern",
        quantity=1,
        work_mode=None,
        clarifying_question="Is this role onsite, remote, or hybrid?",
    )
    assert draft.work_mode is None
    assert draft.clarifying_question is not None


def test_parse_requirement_surfaces_ambiguous_work_mode_gracefully():
    payload = {
        "role_title": "Sales Intern",
        "quantity": 2,
        "work_mode": None,
        "duration": None,
        "compensation": None,
        "required_skills": [],
        "eligibility_rules": {},
        "clarifying_question": "Is this role onsite, remote, or hybrid?",
    }
    with patch("app.agents.requirement_parser.generate", return_value=_fake_result(payload)):
        draft = parse_requirement("need a couple of interns for the sales team")

    assert draft.work_mode is None
    assert draft.clarifying_question == "Is this role onsite, remote, or hybrid?"
