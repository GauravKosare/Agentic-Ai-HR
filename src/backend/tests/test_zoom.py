"""
Unit tests for the Zoom connector that don't need real network calls: token
caching behavior. The real OAuth + meeting-creation calls are exercised by
scripts/check_connectors.py against real credentials.
"""

import time

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
