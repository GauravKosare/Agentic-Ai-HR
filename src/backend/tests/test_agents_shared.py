"""
Unit tests for the shared JSON-extraction helper used by both
requirement_parser.py and form_builder.py.
"""

import pytest

from app.agents._shared import JSONExtractionError, extract_json


def test_extract_json_parses_clean_json():
    assert extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_strips_markdown_fences():
    fenced = '```json\n{"a": 1}\n```'
    assert extract_json(fenced) == {"a": 1}


def test_extract_json_raises_on_invalid_json():
    with pytest.raises(JSONExtractionError):
        extract_json("not json at all")
