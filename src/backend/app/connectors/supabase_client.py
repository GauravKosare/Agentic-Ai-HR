"""
Supabase connector (TRD §5.1).

Two clients on purpose, matching the RLS design in 06-Backend-Schema.md §5.1. Uses
Supabase's new key format (sb_secret_.../sb_publishable_...) rather than the legacy
anon/service_role JWTs — same permissions and drop-in compatible with create_client(),
but each key rotates independently instead of sharing one JWT signing secret.

- `get_service_client()` uses the **secret** key, which bypasses Row Level Security.
  This is what the FastAPI backend/orchestrator uses for agent-generated writes
  (form generation, scoring, etc.) — it must never be exposed to the frontend.
- `get_anon_client()` uses the **publishable** key, which is subject to RLS. This is
  what you'd use to mirror what the frontend does, e.g. in tests that verify RLS
  policies actually isolate one Owner's data from another's. Optional until
  something actually needs RLS-scoped access — not required for the backend to run.
"""

from functools import lru_cache

from supabase import Client, create_client

from app.core.config import get_settings


@lru_cache
def get_service_client() -> Client:
    """Privileged client — bypasses RLS. Backend/orchestrator use only."""
    settings = get_settings()
    settings.require("supabase_url", "supabase_secret_key")
    return create_client(settings.supabase_url, settings.supabase_secret_key)


@lru_cache
def get_anon_client() -> Client:
    """RLS-scoped client — mirrors what the frontend sees. Use with a user JWT for RLS-aware testing."""
    settings = get_settings()
    settings.require("supabase_url", "supabase_publishable_key")
    return create_client(settings.supabase_url, settings.supabase_publishable_key)


def health_check() -> tuple[bool, str]:
    """
    Confirms the service-role client can actually reach the project and authenticate.
    Doesn't assume any application tables exist yet (schema may not be migrated) —
    it just checks that Supabase's auth admin API responds, which only succeeds with
    a valid URL + service-role key.
    """
    try:
        client = get_service_client()
        client.auth.admin.list_users(page=1, per_page=1)
        return True, "Supabase reachable, secret key valid."
    except Exception as exc:  # noqa: BLE001 — surfacing the raw error to the caller is the point here
        return False, f"Supabase health check failed: {exc}"
