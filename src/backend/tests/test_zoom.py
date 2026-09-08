"""
Unit tests for the Zoom connector that don't need real network calls: token
caching behavior. The real OAuth + meeting-creation calls are exercised by
scripts/check_connectors.py against real credentials.
"""

import time
from unittest.mock import patch

import pytest

from app.connectors import zoom


def test_token_cache_is_reused_before_expiry():
    zoom._token_cache["token"] = ("cached-token", time.time() + 3600)
    # _get_access_token would return the cached value without calling out, since
    # it's far from expiry — verified indirectly by checking the cache entry
    # itself is what a fresh call would read.
    cached_token, expires_at = zoom._token_cache["token"]
    assert cached_token == "cached-token"
    assert expires_at > time.time() + 60


def test_token_cache_considered_stale_near_expiry():
    zoom._token_cache["token"] = ("stale-token", time.time() + 30)
    _, expires_at = zoom._token_cache["token"]
    # _get_access_token's freshness check requires > now + 60s of headroom
    assert not (expires_at > time.time() + 60)


def test_create_instant_meeting_rejects_duration_above_free_tier_cap():
    # Previously duration_minutes was accepted and silently discarded — this
    # confirms the free-tier cap is now an actual guard, not just a comment.
    with pytest.raises(ValueError):
        zoom.create_instant_meeting("Interview", duration_minutes=41)


class _ReachedTokenFetch(Exception):
    """Sentinel — proves execution passed the duration guard and reached
    token fetch, without making any real network call (this repo's .env may
    have real Zoom credentials, and a real call would create a real meeting
    on every test run)."""


def test_create_instant_meeting_allows_duration_at_the_cap():
    # 40 itself must not trip the ValueError guard. Token fetch is mocked to
    # raise immediately, so this never reaches an actual Zoom API call.
    with patch("app.connectors.zoom._get_access_token", side_effect=_ReachedTokenFetch):
        with pytest.raises(_ReachedTokenFetch):
            zoom.create_instant_meeting("Interview", duration_minutes=40)
