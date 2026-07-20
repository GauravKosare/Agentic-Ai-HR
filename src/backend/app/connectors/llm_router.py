"""
LLM Router — TRD §3.1a.

Every LLM call in the system goes through `generate()` instead of calling a model
directly:

    1. Try Gemini's model CHAIN for the task's tier, in order (e.g. reasoning:
       gemini-3.5-flash -> gemini-3-flash). A quota (429) error on one model moves
       to the next model in the same chain, not straight to Groq — Gemini's free
       daily quota is per-model, so a second Gemini model is still "free money"
       before paying the cost of a provider switch.
    2. Once every model in Gemini's chain for that tier returns quota-exceeded,
       walk Groq's chain for the same tier the same way (e.g. reasoning:
       openai/gpt-oss-120b -> llama-3.3-70b-versatile -> qwen/qwen3.6-27b).
    3. If every model in both providers' chains is exhausted, raise
       AIQuotaExhausted instead of falling through to any paid model. The caller
       is responsible for:
         - setting the system-wide `ai_paused` flag (see 06-Backend-Schema.md,
           audit_log action 'ai_quota_paused'),
         - sending the Owner one reminder Email,
         - and clearing the flag once `resume_at` has passed (action
           'ai_quota_resumed').

This module intentionally does NOT try a paid model as a fallback of last resort —
that would silently break the project's zero-cost policy (07-Financial-
Subscription-Tracking.md). Model chains live in app/core/config.py, sourced from
live account quota data, not vendor marketing pages — re-verify periodically,
free-tier per-model limits vary by account and change over time.

Task-specific routing: callers pass a `Task` (one per named agent in the TRD/
Workflow docs), not a raw "reasoning"/"light" tier — the mapping from task to tier
lives in one place here (TASK_TIER), matching TRD §3.1a's explicit list:
"Gemini for reasoning-heavy calls (interview dialogue, scoring, requirement
parsing); Gemini light models for high-volume/light calls (dedup checks, simple
classification, resume field extraction)." Form generation is grouped with the
reasoning tier — it's structured creative generation, the same shape of work as
requirement parsing, not a high-volume/light lookup.

NOTE — shared-provider risk: speech_to_text.py also calls Groq (for STT). A Groq
outage or account-wide issue affects both this module's fallback path AND STT at
the same time — see 07-Financial-Subscription-Tracking.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.connectors._shared import next_gemini_reset, try_chain
from app.core.config import get_settings


class Tier(str, Enum):
    """Internal model tier. Callers should use Task, not this, directly."""

    REASONING = "reasoning"
    LIGHT = "light"


class Task(str, Enum):
    """
    One value per LLM-calling agent named in the TRD/Workflow docs. Adding a new
    call site means adding a Task here and a line in TASK_TIER — never picking a
    tier inline at the call site, so the TRD's task->tier mapping stays enforced
    in one place.
    """

    REQUIREMENT_PARSING = "requirement_parsing"  # TRD §3.1 — Requirement Parser Agent
    FORM_GENERATION = "form_generation"  # TRD §3.2 — Form Builder Agent
    RESUME_PARSING = "resume_parsing"  # TRD §4 — resume field extraction (replaces Affinda)
    DEDUP_CLASSIFICATION = "dedup_classification"  # TRD §3.4 — Response Monitor Agent (dedup/simple classification)
    INTERVIEW_DIALOGUE = "interview_dialogue"  # TRD §3.7 — Meeting Bot / Live Interview Agent
    SCORING = "scoring"  # TRD §3.8 — Scoring Agent


TASK_TIER: dict[Task, Tier] = {
    Task.REQUIREMENT_PARSING: Tier.REASONING,
    Task.FORM_GENERATION: Tier.REASONING,
    Task.RESUME_PARSING: Tier.LIGHT,
    Task.DEDUP_CLASSIFICATION: Tier.LIGHT,
    Task.INTERVIEW_DIALOGUE: Tier.REASONING,
    Task.SCORING: Tier.REASONING,
}


@dataclass
class LLMResult:
    text: str
    provider: str  # "gemini" | "groq"
    model: str
    task: Task


class AIQuotaExhausted(Exception):
    """
    Raised when every model in both Gemini's and Groq's chains for this task's
    tier is exhausted for the day. Callers must NOT catch this and fall back to a
    paid model — catch it to trigger the pause-and-notify flow in TRD §3.1a instead.
    """

    def __init__(self, resume_at, detail: str):
        self.resume_at = resume_at
        self.detail = detail
        super().__init__(f"Both Gemini's and Groq's free-tier model chains are exhausted. {detail}")


def _call_gemini(model: str, prompt: str, task: Task) -> LLMResult:
    from google import genai

    settings = get_settings()
    settings.require("gemini_api_key")
    client = genai.Client(api_key=settings.gemini_api_key)
    response = client.models.generate_content(model=model, contents=prompt)
    return LLMResult(text=response.text, provider="gemini", model=model, task=task)


def _call_groq(model: str, prompt: str, task: Task) -> LLMResult:
    from groq import Groq

    settings = get_settings()
    settings.require("groq_api_key")
    client = Groq(api_key=settings.groq_api_key)
    completion = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return LLMResult(text=completion.choices[0].message.content, provider="groq", model=model, task=task)


def generate(prompt: str, task: Task) -> LLMResult:
    """
    The single entry point every agent should call for an LLM completion. `task`
    is required (not defaulted) so every call site is explicit about which named
    agent it's acting as — that's what TASK_TIER routes on.

    Raises AIQuotaExhausted (not a generic exception) when every model in both
    providers' chains is out for the day, so callers can implement the
    pause-and-notify behavior distinctly from a genuine bug/outage.
    """
    settings = get_settings()
    tier = TASK_TIER[task]

    gemini_models = settings.gemini_reasoning_chain if tier == Tier.REASONING else settings.gemini_light_chain
    groq_models = settings.groq_reasoning_chain if tier == Tier.REASONING else settings.groq_light_chain

    result, gemini_errors = try_chain(gemini_models, lambda model: _call_gemini(model, prompt, task))
    if result is not None:
        return result

    result, groq_errors = try_chain(groq_models, lambda model: _call_groq(model, prompt, task))
    if result is not None:
        return result

    raise AIQuotaExhausted(
        resume_at=next_gemini_reset(),
        detail=(
            f"Task: {task.value} (tier: {tier.value}). "
            f"Gemini chain exhausted ({'; '.join(gemini_errors)}). "
            f"Groq chain exhausted ({'; '.join(groq_errors)}). "
            "Resuming automatically once Gemini's daily quota resets — "
            "verify Groq's own reset timing against current docs (07-Financial-Subscription-Tracking.md)."
        ),
    )


def health_check() -> tuple[bool, str]:
    """Cheap connectivity check for both providers — one token in, no real cost against the free tier."""
    try:
        result = generate("Reply with the single word: ok", task=Task.DEDUP_CLASSIFICATION)
        return True, f"OK via {result.provider} ({result.model})"
    except AIQuotaExhausted as exc:
        return False, f"Every free-tier model is exhausted right now — resumes at {exc.resume_at.isoformat()}"
    except Exception as exc:  # noqa: BLE001
        return False, f"LLM Router health check failed: {exc}"
