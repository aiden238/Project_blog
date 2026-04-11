from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.dialects import postgresql

from src.models import Outbox
from src.workers.outbox_dispatcher import (
    OutboxDispatcher,
    build_outbox_claim_query,
    build_retry_available_at,
)


class FakeScalarResult:
    def __init__(self, values):
        self._values = values

    def __iter__(self):
        return iter(self._values)


class FakeSession:
    def __init__(self, entries: list[Outbox]) -> None:
        self.entries = entries

    def scalars(self, _statement: object):
        return FakeScalarResult(self.entries)


def build_entry(*, attempts: int = 0) -> Outbox:
    return Outbox(
        id=1,
        target="notion",
        item_id="item-1",
        event_type="draft_ready",
        payload={"title": "Example"},
        status="pending",
        attempts=attempts,
        available_at=datetime(2026, 4, 26, tzinfo=timezone.utc),
    )


def test_build_outbox_claim_query_uses_skip_locked() -> None:
    query = build_outbox_claim_query(
        now=datetime(2026, 4, 26, tzinfo=timezone.utc),
        limit=5,
    )

    compiled = str(
        query.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )

    assert "FOR UPDATE SKIP LOCKED" in compiled


def test_dispatch_once_marks_entry_sent() -> None:
    entry = build_entry()
    dispatcher = OutboxDispatcher(
        FakeSession([entry]),
        handlers={"notion": lambda _entry: None},
        max_attempts=5,
    )

    result = dispatcher.dispatch_once(now=datetime(2026, 4, 26, tzinfo=timezone.utc))

    assert result.sent == 1
    assert entry.status == "sent"


def test_dispatch_once_marks_entry_dead_after_max_attempts(monkeypatch) -> None:
    entry = build_entry(attempts=4)
    logged_alerts: list[dict] = []
    monkeypatch.setattr(
        "src.workers.outbox_dispatcher.append_json_log",
        lambda _path, payload: logged_alerts.append(payload),
    )
    dispatcher = OutboxDispatcher(
        FakeSession([entry]),
        handlers={"notion": lambda _entry: (_ for _ in ()).throw(RuntimeError("boom"))},
        max_attempts=5,
    )

    result = dispatcher.dispatch_once(now=datetime(2026, 4, 26, tzinfo=timezone.utc))

    assert result.dead == 1
    assert entry.status == "dead"
    assert logged_alerts[0]["kind"] == "outbox_dead"


def test_build_retry_available_at_uses_backoff_schedule() -> None:
    now = datetime(2026, 4, 26, tzinfo=timezone.utc)

    available_at = build_retry_available_at(attempts=2, now=now)

    assert int((available_at - now).total_seconds()) == 300
