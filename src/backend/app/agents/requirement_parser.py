"""
Requirement Parser Agent — TRD §3.1, Workflow Stage 1.

Turns the Owner's plain-language hiring brief into a structured requisition
matching the `requisitions` table (06-Backend-Schema.md §2.2). Routed through
the LLM Router (TRD §3.1a) under Task.REQUIREMENT_PARSING — reasoning tier.

Deliberately does NOT persist to Supabase. This module's job is text-in,
validated-structure-out; saving belongs to whatever calls it (an API endpoint,
once one exists) once it also has an owner_id, which nothing in this repo
produces yet (no auth/signup flow built). Keeping it a pure function makes it
trivially testable without a live database and reusable from any future entry
point (HTTP handler, CLI, batch job).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, model_validator

from app.agents._shared import JSONExtractionError, extract_json
from app.connectors.llm_router import Task, generate


class RequisitionDraft(BaseModel):
    """
    Field names/types mirror the `requisitions` table columns directly (not a
    separate DTO translated later) — so the FastAPI layer can eventually call
    `.model_dump(exclude={"clarifying_question"})` straight into an insert,
    with one paired the schema and this model change together instead of a
    silent drift between "what the agent produces" and "what the table stores".
    """

    role_title: str
    quantity: int = Field(gt=0)
    # Nullable, unlike role_title/quantity: the prompt explicitly permits the
    # model to leave work_mode unset when genuinely ambiguous (a real, common
    # case — "hiring for the sales team" says nothing about onsite/remote/
    # hybrid). A live test against this exact case is what caught the original
    # bug here: the prompt allowed a null work_mode, but the schema required
    # one, so a legitimate "I need to ask" response crashed instead of
    # surfacing gracefully. The model-level validator below closes that gap:
    # null is only ever accepted paired with a clarifying_question, never
    # silently.
    work_mode: Literal["onsite", "remote", "hybrid"] | None = None
    duration: str | None = None
    compensation: str | None = None
    required_skills: list[str] = Field(default_factory=list)
    # Free-form JSONB in the DB (06-Backend-Schema.md) — deliberately not a fixed
    # Pydantic sub-model, since eligibility criteria vary too much role-to-role
    # ("final-year students only", "3+ years experience", "must relocate") to
    # usefully constrain with a rigid schema. seniority_level also lands here:
    # TRD §3.1 lists it as an extracted field, but the DB schema has no
    # dedicated column for it — rather than let that TRD/schema gap silently
    # drop the field, it's stored as eligibility_rules["seniority_level"].
    eligibility_rules: dict[str, Any] = Field(default_factory=dict)

    # Not a DB column. TRD §3.1 / Workflow Stage 1 / UI-UX §4.1 describe the
    # Owner seeing the structured summary card AND (when something's genuinely
    # unclear) one clarifying question AT THE SAME TIME — not as a blocking
    # either/or. Modeling this as one optional field on the draft, rather than
    # a separate "needs clarification" return type, matches that: the caller
    # always has a usable draft, and separately knows whether to also surface
    # a question. Per TRD, this is capped at one question, never a list.
    clarifying_question: str | None = None

    @model_validator(mode="after")
    def _null_work_mode_must_carry_a_question(self) -> "RequisitionDraft":
        """
        Enforces TRD's "not silent assumption" principle at the schema level,
        not just by convention: a null work_mode is only ever valid alongside
        a clarifying_question explaining why. Without this, a future prompt
        change could reintroduce a draft that's silently half-blank with no
        visible reason — this makes that state unrepresentable, not just
        discouraged.
        """
        if self.work_mode is None and not self.clarifying_question:
            raise ValueError("work_mode is null but no clarifying_question was given to explain why")
        return self


class RequirementParsingError(Exception):
    """
    Raised when the model's response can't be turned into a RequisitionDraft at
    all — not valid JSON, or missing a field with no reasonable fallback (e.g.
    role_title). This is a distinct failure mode from clarifying_question: that
    field means the model successfully extracted a draft but flagged one open
    question: this exception means extraction itself failed. Collapsing the two
    would let a genuine model/prompt failure quietly masquerade as a normal
    "just ask the Owner" case.
    """

    def __init__(self, detail: str, raw_response: str):
        self.detail = detail
        self.raw_response = raw_response
        super().__init__(f"Failed to parse requirement: {detail}")


_SCHEMA_INSTRUCTIONS = """\
You are the Requirement Parser for a hiring assistant. The Owner has described \
a role they want to hire for, in plain language. Extract it into JSON matching \
exactly this shape:

{
  "role_title": string,
  "quantity": integer (number of openings, default 1 if not stated),
  "work_mode": "onsite" | "remote" | "hybrid",
  "duration": string or null (e.g. "3 months", "permanent"),
  "compensation": string or null (e.g. "₹15,000/month", "12 LPA"),
  "required_skills": array of strings,
  "eligibility_rules": object (free-form key/value — e.g. seniority_level, \
minimum experience, education requirement, anything else stated),
  "clarifying_question": string or null
}

Rules:
- Fill in every field you can confidently infer from the brief. Do not leave \
role_title, quantity, or work_mode null unless truly not determinable — pick \
the most reasonable interpretation from context first.
- Only set clarifying_question if exactly ONE detail is genuinely ambiguous or \
missing in a way that would materially change the requisition (e.g. "Should \
this be open to final-year students or only graduates?"). Never ask more than \
one question. Leave it null if the brief is clear enough to proceed.
- Output ONLY the JSON object. No commentary, no markdown code fences.

Owner's brief:
\"\"\"
{brief}
\"\"\"
"""


def _build_prompt(raw_brief_text: str) -> str:
    # Plain substring replace, not str.format() — the template contains literal
    # JSON braces ({ }), which .format() would misparse as its own placeholders.
    return _SCHEMA_INSTRUCTIONS.replace("{brief}", raw_brief_text.strip())


def parse_requirement(raw_brief_text: str) -> RequisitionDraft:
    """
    The single entry point. Raises RequirementParsingError on a genuine
    extraction failure. Does NOT catch AIQuotaExhausted — that propagates to
    the caller by design (TRD §3.1a: the caller is responsible for the
    pause-and-notify flow, not each individual agent), so this function stays
    focused on parsing, not on quota-exhaustion UX.
    """
    if not raw_brief_text or not raw_brief_text.strip():
        raise RequirementParsingError("empty brief", raw_brief_text)

    result = generate(_build_prompt(raw_brief_text), task=Task.REQUIREMENT_PARSING)

    try:
        payload = extract_json(result.text)
    except JSONExtractionError as exc:
        raise RequirementParsingError(exc.detail, exc.raw_response) from exc

    try:
        return RequisitionDraft.model_validate(payload)
    except ValidationError as exc:
        raise RequirementParsingError(f"model output didn't match the required schema: {exc}", result.text) from exc
