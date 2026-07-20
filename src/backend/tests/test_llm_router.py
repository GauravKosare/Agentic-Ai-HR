"""
Unit tests for the LLM Router's task-to-tier mapping (TRD §3.1a). Chain-walking
logic itself is tested generically in test_shared.py; the real Gemini/Groq calls
are exercised by scripts/check_connectors.py against real credentials.
"""

from app.connectors.llm_router import TASK_TIER, Task, Tier


def test_every_task_has_a_tier_mapping():
    for task in Task:
        assert task in TASK_TIER


def test_task_tier_matches_trd_section_3_1a():
    # "Gemini for reasoning-heavy calls (interview dialogue, scoring, requirement
    #  parsing); Gemini light models for high-volume/light calls (dedup checks,
    #  simple classification, resume field extraction)." — TRD §3.1a
    assert TASK_TIER[Task.REQUIREMENT_PARSING] == Tier.REASONING
    assert TASK_TIER[Task.INTERVIEW_DIALOGUE] == Tier.REASONING
    assert TASK_TIER[Task.SCORING] == Tier.REASONING
    assert TASK_TIER[Task.RESUME_PARSING] == Tier.LIGHT
    assert TASK_TIER[Task.DEDUP_CLASSIFICATION] == Tier.LIGHT
