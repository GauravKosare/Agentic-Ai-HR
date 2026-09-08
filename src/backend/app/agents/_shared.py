"""
Shared helpers for agents that ask the LLM Router for a JSON response and
validate it against a Pydantic model — currently requirement_parser.py and
form_builder.py. Not a public API on its own; each agent wraps
JSONExtractionError in its own domain-specific exception type rather than
letting it leak as-is, same as connectors/_shared.py does for the
quota-chain pattern.
"""

from __future__ import annotations

import json
import re

_JSON_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


class JSONExtractionError(Exception):
    """Raised when the model's response isn't valid JSON at all, even after
    stripping markdown fences."""

    def __init__(self, detail: str, raw_response: str):
        self.detail = detail
        self.raw_response = raw_response
        super().__init__(detail)


def extract_json(model_text: str) -> dict:
    """
    Strips markdown code fences if the model added them anyway (common even
    with an explicit "no fences" instruction) before parsing.
    """
    cleaned = _JSON_FENCE.sub("", model_text.strip()).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise JSONExtractionError(f"model response was not valid JSON: {exc}", model_text) from exc
