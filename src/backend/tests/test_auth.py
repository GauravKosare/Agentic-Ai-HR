"""
Unit tests for the Owner auth dependency. JWT verification (_decode) is mocked —
these test the claims-to-Owner resolution and the aal2 requirement, not real
JWKS/signature checks (that's exercised live once a real Supabase user exists).
"""

from unittest.mock import patch

import pytest

from app.core.auth import AuthError, Owner, _owner_from_claims, get_current_owner


class _FakeResponse:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        return _FakeResponse(self._rows)


class _FakeClient:
    def __init__(self, rows):
        self._rows = rows

    def table(self, name):
        return _FakeQuery(self._rows)


_OWNER_ROW = {
    "owner_id": "11111111-1111-1111-1111-111111111111",
    "auth_user_id": "22222222-2222-2222-2222-222222222222",
    "email": "owner@example.com",
    "full_name": "Gaurav",
}


def test_aal2_token_resolves_to_owner():
    claims = {"sub": _OWNER_ROW["auth_user_id"], "aal": "aal2"}
    with patch("app.core.auth.get_service_client", return_value=_FakeClient([_OWNER_ROW])):
        owner = _owner_from_claims(claims)
    assert isinstance(owner, Owner)
    assert owner.owner_id == _OWNER_ROW["owner_id"]
    assert owner.email == "owner@example.com"


def test_aal1_token_is_rejected_mfa_required():
    claims = {"sub": _OWNER_ROW["auth_user_id"], "aal": "aal1"}
    with patch("app.core.auth.get_service_client", return_value=_FakeClient([_OWNER_ROW])):
        with pytest.raises(AuthError) as exc:
            _owner_from_claims(claims)
    assert exc.value.status_code == 403
    assert "multi-factor" in exc.value.detail["detail"]


def test_authenticated_but_no_owner_row_is_forbidden():
    claims = {"sub": "unknown-uuid", "aal": "aal2"}
    with patch("app.core.auth.get_service_client", return_value=_FakeClient([])):
        with pytest.raises(AuthError) as exc:
            _owner_from_claims(claims)
    assert exc.value.status_code == 403
    assert "not provisioned" in exc.value.detail["detail"]


def test_token_without_subject_is_rejected():
    with patch("app.core.auth.get_service_client", return_value=_FakeClient([])):
        with pytest.raises(AuthError):
            _owner_from_claims({"aal": "aal2"})


def test_get_current_owner_rejects_missing_header():
    with pytest.raises(AuthError) as exc:
        get_current_owner(authorization="")
    assert exc.value.status_code == 401


def test_get_current_owner_rejects_non_bearer_scheme():
    with pytest.raises(AuthError) as exc:
        get_current_owner(authorization="Basic abc123")
    assert exc.value.status_code == 401


def test_get_current_owner_happy_path_delegates_to_decode_and_resolve():
    claims = {"sub": _OWNER_ROW["auth_user_id"], "aal": "aal2"}
    with (
        patch("app.core.auth._decode", return_value=claims) as mock_decode,
        patch("app.core.auth.get_service_client", return_value=_FakeClient([_OWNER_ROW])),
    ):
        owner = get_current_owner(authorization="Bearer some.jwt.token")
    mock_decode.assert_called_once_with("some.jwt.token")
    assert owner.owner_id == _OWNER_ROW["owner_id"]
