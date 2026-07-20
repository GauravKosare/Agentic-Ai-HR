"""
Unit tests for the shared chain-walking helpers used by both llm_router.py and
speech_to_text.py: quota-error detection, generic chain-trying, and the daily
reset-time calculation. The real Gemini/Groq calls are exercised by
scripts/check_connectors.py against real credentials, not here.
"""

import datetime as dt

from app.connectors._shared import is_quota_error, next_gemini_reset, try_chain
from app.core.config import _split


class FakeQuotaError(Exception):
    status_code = 429


def test_is_quota_error_detects_status_code():
    assert is_quota_error(FakeQuotaError("rate limited")) is True


def test_is_quota_error_detects_message_text():
    assert is_quota_error(Exception("RESOURCE_EXHAUSTED: quota exceeded")) is True


def test_is_quota_error_ignores_unrelated_errors():
    assert is_quota_error(ValueError("bad API key")) is False


def test_next_gemini_reset_is_in_the_future():
    reset = next_gemini_reset()
    assert reset > dt.datetime.now(reset.tzinfo)
    assert reset.hour == 0 and reset.minute == 0


def test_split_parses_comma_separated_chain():
    assert _split("gemini-3.5-flash, gemini-3-flash ,") == ["gemini-3.5-flash", "gemini-3-flash"]


def test_try_chain_uses_first_model_that_succeeds():
    result, errors = try_chain(["model-a", "model-b"], lambda model: f"result-from-{model}")
    assert result == "result-from-model-a"
    assert errors == []


def test_try_chain_falls_through_quota_errors_to_next_model():
    def fake_call(model):
        if model == "model-a":
            raise FakeQuotaError("exhausted")
        return f"result-from-{model}"

    result, errors = try_chain(["model-a", "model-b"], fake_call)
    assert result == "result-from-model-b"
    assert len(errors) == 1 and "model-a" in errors[0]


def test_try_chain_returns_none_when_every_model_is_exhausted():
    def fake_call(model):
        raise FakeQuotaError("exhausted")

    result, errors = try_chain(["model-a", "model-b"], fake_call)
    assert result is None
    assert len(errors) == 2


def test_try_chain_raises_immediately_on_non_quota_error():
    def fake_call(model):
        raise ValueError("bad API key")

    try:
        try_chain(["model-a", "model-b"], fake_call)
        assert False, "expected ValueError to propagate"
    except ValueError:
        pass
