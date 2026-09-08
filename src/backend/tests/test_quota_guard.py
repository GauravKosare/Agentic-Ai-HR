"""
Unit tests for the quota-pause guard (TRD §3.1a). Supabase and email are both
faked/mocked — this tests pause/resume state derivation and the notify-once
behavior, not real network calls.
"""

import datetime as dt
from unittest.mock import patch

from app.connectors.llm_router import AIQuotaExhausted
from app.core import quota_guard


class _FakeResponse:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    """Minimal stand-in for supabase-py's fluent query builder: every filter
    method returns self, and .execute() reads from the parent fake client's
    canned rows (for a select) or records the insert (for an insert)."""

    def __init__(self, table_name, store):
        self._table_name = table_name
        self._store = store
        self._insert_payload = None

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def in_(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def insert(self, payload):
        self._insert_payload = payload
        return self

    def execute(self):
        if self._insert_payload is not None:
            self._store.inserted.append({"table": self._table_name, "payload": self._insert_payload})
            return _FakeResponse([self._insert_payload])
        if self._table_name == "audit_log":
            return _FakeResponse(self._store.audit_log_rows)
        if self._table_name == "owners":
            return _FakeResponse(self._store.owners_rows)
        return _FakeResponse([])


class FakeSupabaseClient:
    def __init__(self, audit_log_rows=None, owners_rows=None):
        self.audit_log_rows = audit_log_rows or []
        self.owners_rows = owners_rows or []
        self.inserted = []

    def table(self, name):
        return _FakeQuery(name, self)


def _make_exc(resume_at):
    return AIQuotaExhausted(resume_at=resume_at, detail="test exhaustion")


def test_is_ai_paused_false_when_no_audit_rows():
    fake = FakeSupabaseClient(audit_log_rows=[])
    with patch("app.core.quota_guard.get_service_client", return_value=fake):
        paused, resume_at = quota_guard.is_ai_paused()
    assert paused is False
    assert resume_at is None


def test_is_ai_paused_true_when_recent_pause_not_yet_expired():
    future = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1)
    fake = FakeSupabaseClient(
        audit_log_rows=[{"action": "ai_quota_paused", "details": {"resume_at": future.isoformat()}, "created_at": "x"}]
    )
    with patch("app.core.quota_guard.get_service_client", return_value=fake):
        paused, resume_at = quota_guard.is_ai_paused()
    assert paused is True
    assert resume_at == future


def test_is_ai_paused_false_and_logs_resume_once_expired():
    past = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1)
    fake = FakeSupabaseClient(
        audit_log_rows=[{"action": "ai_quota_paused", "details": {"resume_at": past.isoformat()}, "created_at": "x"}]
    )
    with patch("app.core.quota_guard.get_service_client", return_value=fake):
        paused, resume_at = quota_guard.is_ai_paused()
    assert paused is False
    assert resume_at is None
    assert any(row["payload"]["action"] == "ai_quota_resumed" for row in fake.inserted)


def test_is_ai_paused_false_when_latest_row_is_already_a_resume():
    fake = FakeSupabaseClient(
        audit_log_rows=[{"action": "ai_quota_resumed", "details": {}, "created_at": "x"}]
    )
    with patch("app.core.quota_guard.get_service_client", return_value=fake):
        paused, _ = quota_guard.is_ai_paused()
    assert paused is False


def test_record_and_notify_logs_pause_and_emails_active_owners():
    fake = FakeSupabaseClient(audit_log_rows=[], owners_rows=[{"email": "owner@example.com", "full_name": "Gaurav"}])
    exc = _make_exc(dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=2))
    with (
        patch("app.core.quota_guard.get_service_client", return_value=fake),
        patch("app.core.quota_guard.email_connector.send_plain_email") as mock_send,
    ):
        quota_guard.record_and_notify(exc)

    assert any(row["payload"]["action"] == "ai_quota_paused" for row in fake.inserted)
    mock_send.assert_called_once()
    assert mock_send.call_args.kwargs["to_email"] == "owner@example.com"


def test_record_and_notify_does_not_double_log_within_the_same_pause_window():
    future = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1)
    fake = FakeSupabaseClient(
        audit_log_rows=[{"action": "ai_quota_paused", "details": {"resume_at": future.isoformat()}, "created_at": "x"}],
        owners_rows=[{"email": "owner@example.com", "full_name": "Gaurav"}],
    )
    exc = _make_exc(future)
    with (
        patch("app.core.quota_guard.get_service_client", return_value=fake),
        patch("app.core.quota_guard.email_connector.send_plain_email") as mock_send,
    ):
        quota_guard.record_and_notify(exc)

    # already paused this window - no new pause row, no new email
    assert not any(row["payload"].get("action") == "ai_quota_paused" for row in fake.inserted)
    mock_send.assert_not_called()


def test_record_and_notify_swallows_email_failure_without_raising():
    fake = FakeSupabaseClient(audit_log_rows=[], owners_rows=[{"email": "owner@example.com", "full_name": "Gaurav"}])
    exc = _make_exc(dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=2))
    with (
        patch("app.core.quota_guard.get_service_client", return_value=fake),
        patch("app.core.quota_guard.email_connector.send_plain_email", side_effect=RuntimeError("brevo down")),
    ):
        quota_guard.record_and_notify(exc)  # must not raise
    assert any(row["payload"]["action"] == "ai_quota_paused" for row in fake.inserted)


def test_record_and_notify_handles_zero_owners_gracefully():
    fake = FakeSupabaseClient(audit_log_rows=[], owners_rows=[])
    exc = _make_exc(dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=2))
    with (
        patch("app.core.quota_guard.get_service_client", return_value=fake),
        patch("app.core.quota_guard.email_connector.send_plain_email") as mock_send,
    ):
        quota_guard.record_and_notify(exc)  # must not raise
    mock_send.assert_not_called()
    assert any(row["payload"]["action"] == "ai_quota_paused" for row in fake.inserted)
