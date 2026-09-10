"""
Owner authentication — 06-Backend-Schema.md §5.1a, per the council decision
(docs/decisions/council-transcript-20260910-200541.md).

`get_current_owner` is a FastAPI dependency every Owner-facing endpoint depends
on. It:
  1. Reads the `Authorization: Bearer <jwt>` header.
  2. Verifies the JWT against Supabase's JWKS endpoint (asymmetric signing keys,
     the modern default) — or an HS256 shared secret if SUPABASE_JWT_SECRET is
     set for a legacy project.
  3. Requires `aal == "aal2"` — password AND a passed second factor (TOTP MFA).
     An `aal1` token (password only) is rejected: MFA is mandatory on the Owner
     account for a system holding candidate PII.
  4. Resolves the token's `sub` (the auth.users UUID) to a row in `public.owners`.
     Authenticated-but-not-provisioned (valid token, no owners row) is a 403 —
     public sign-ups are disabled, Owner rows are created deliberately.

This is the PRIMARY authorization layer. RLS is the second layer beneath it
(§5.1) — the backend uses the service-role key which bypasses RLS, so every
query must also filter by the returned `owner.owner_id` in application code.
"""

from __future__ import annotations

from functools import lru_cache

import jwt
from fastapi import Depends, Header, HTTPException, status
from jwt import PyJWKClient
from pydantic import BaseModel

from app.connectors.supabase_client import get_service_client
from app.core.config import get_settings

_AUDIENCE = "authenticated"


class Owner(BaseModel):
    owner_id: str
    auth_user_id: str
    email: str
    full_name: str | None = None


class AuthError(HTTPException):
    def __init__(self, detail: str, code: int = status.HTTP_401_UNAUTHORIZED):
        super().__init__(status_code=code, detail={"error": "auth_failed", "detail": detail})


@lru_cache
def _jwks_client() -> PyJWKClient:
    base = get_settings().supabase_url.rstrip("/")
    # PyJWKClient caches fetched keys internally and refreshes on unknown kid.
    return PyJWKClient(f"{base}/auth/v1/.well-known/jwks.json")


def _decode(token: str) -> dict:
    settings = get_settings()
    try:
        if settings.supabase_jwt_secret:
            return jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience=_AUDIENCE,
            )
        signing_key = _jwks_client().get_signing_key_from_jwt(token).key
        return jwt.decode(
            token,
            signing_key,
            algorithms=["ES256", "RS256"],
            audience=_AUDIENCE,
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthError(f"invalid token: {exc}") from exc
    except Exception as exc:  # noqa: BLE001 — JWKS fetch / network failures land here
        raise AuthError(f"could not verify token: {exc}") from exc


def _owner_from_claims(claims: dict) -> Owner:
    if claims.get("aal") != "aal2":
        raise AuthError(
            "multi-factor authentication is required for this account",
            code=status.HTTP_403_FORBIDDEN,
        )

    auth_user_id = claims.get("sub")
    if not auth_user_id:
        raise AuthError("token has no subject")

    rows = (
        get_service_client()
        .table("owners")
        .select("owner_id, auth_user_id, email, full_name")
        .eq("auth_user_id", auth_user_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not rows:
        raise AuthError(
            "this account is authenticated but not provisioned as an Owner",
            code=status.HTTP_403_FORBIDDEN,
        )
    return Owner(**rows[0])


def get_current_owner(authorization: str = Header(default="")) -> Owner:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise AuthError("missing or malformed Authorization header")
    return _owner_from_claims(_decode(token))
