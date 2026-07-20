"""
Shared helpers for connectors that implement a "try a chain of free-tier models,
move to the next one on quota exhaustion" pattern — currently llm_router.py and
speech_to_text.py. Not a public API on its own; import from the connector module
that owns the concept you need (e.g. `AIQuotaExhausted` from llm_router).
"""

from __future__ import annotations

import datetime as dt


def is_quota_error(exc: Exception) -> bool:
    """
    SDK exception types vary by version and by provider, so this checks the things
    that are stable across Google's, Groq's, and any similar client library: an
    HTTP 429 status, or the words a quota/rate-limit error reliably uses.
    """
    status_code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    if status_code == 429:
        return True
    message = str(exc).lower()
    return any(term in message for term in ("429", "quota", "rate limit", "resource_exhausted", "resource exhausted"))


def try_chain(models: list[str], call_fn):
    """
    Tries each model in `models` in order, calling `call_fn(model)`. Returns
    (result, errors) — result is None only if every model in the chain hit a
    quota error, in which case errors holds one message per model. A non-quota
    error (bad key, network, etc.) raises immediately rather than being swallowed
    and retried against the next model.
    """
    errors: list[str] = []
    for model in models:
        try:
            return call_fn(model), errors
        except Exception as exc:  # noqa: BLE001
            if not is_quota_error(exc):
                raise
            errors.append(f"{model}: {exc}")
    return None, errors


def next_gemini_reset() -> dt.datetime:
    """Gemini's daily free-tier quota resets at 00:00 Pacific Time (TRD §3.1a)."""
    try:
        from zoneinfo import ZoneInfo

        pacific = ZoneInfo("America/Los_Angeles")
    except Exception:  # pragma: no cover — tzdata missing on some minimal environments
        pacific = dt.timezone(dt.timedelta(hours=-8))
    now_pacific = dt.datetime.now(pacific)
    reset = (now_pacific + dt.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return reset
