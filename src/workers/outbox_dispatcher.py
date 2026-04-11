from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from src.logging_utils import append_json_log
from src.models import Outbox

OUTBOX_RETRY_SCHEDULE = (
    timedelta(minutes=1),
    timedelta(minutes=5),
    timedelta(minutes=15),
    timedelta(hours=1),
    timedelta(hours=6),
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def build_retry_available_at(*, attempts: int, now: datetime | None = None) -> datetime:
    schedule_index = min(max(attempts - 1, 0), len(OUTBOX_RETRY_SCHEDULE) - 1)
    return (now or utcnow()) + OUTBOX_RETRY_SCHEDULE[schedule_index]


def build_outbox_claim_query(
    *,
    now: datetime | None = None,
    limit: int = 10,
) -> Select[tuple[Outbox]]:
    return (
        select(Outbox)
        .where(Outbox.status.in_(("pending", "failed")))
        .where(Outbox.available_at <= (now or utcnow()))
        .order_by(Outbox.available_at, Outbox.id)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )


@dataclass
class OutboxDispatchResult:
    claimed: int = 0
    sent: int = 0
    failed: int = 0
    dead: int = 0


class OutboxDispatcher:
    def __init__(
        self,
        session: Session,
        *,
        handlers: Mapping[str, Callable[[Outbox], None]],
        max_attempts: int,
    ) -> None:
        self.session = session
        self.handlers = handlers
        self.max_attempts = max_attempts

    def dispatch_once(
        self,
        *,
        limit: int = 10,
        now: datetime | None = None,
    ) -> OutboxDispatchResult:
        current_time = now or utcnow()
        query = build_outbox_claim_query(now=current_time, limit=limit)
        entries = list(self.session.scalars(query))
        result = OutboxDispatchResult(claimed=len(entries))

        for entry in entries:
            entry.status = "processing"
            entry.locked_at = current_time
            entry.attempts = int(entry.attempts or 0) + 1

            try:
                handler = self.handlers[entry.target]
                handler(entry)
                entry.status = "sent"
                entry.processed_at = current_time
                entry.last_error = None
                result.sent += 1
            except Exception as error:
                entry.last_error = str(error)
                if entry.attempts >= self.max_attempts:
                    entry.status = "dead"
                    entry.processed_at = current_time
                    append_json_log(
                        "alerts.log",
                        {
                            "kind": "outbox_dead",
                            "outbox_id": entry.id,
                            "target": entry.target,
                            "item_id": entry.item_id,
                            "error": str(error),
                        },
                    )
                    result.dead += 1
                else:
                    entry.status = "failed"
                    entry.available_at = build_retry_available_at(
                        attempts=entry.attempts,
                        now=current_time,
                    )
                    result.failed += 1

        return result
