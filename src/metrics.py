from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.models import Metric


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def record_metric(
    session: Session,
    *,
    kind: str,
    target_id: str | None,
    value: float,
    meta: dict[str, Any] | None = None,
    recorded_at: datetime | None = None,
) -> Metric:
    metric = Metric(
        kind=kind,
        target_id=target_id,
        value=value,
        meta=meta or {},
        recorded_at=recorded_at or utcnow(),
    )
    session.add(metric)
    return metric


def count_metrics_in_window(
    session: Session,
    *,
    kind: str,
    target_id: str,
    window: timedelta,
) -> int:
    threshold = utcnow() - window
    stmt = (
        select(func.count(Metric.id))
        .where(Metric.kind == kind)
        .where(Metric.target_id == target_id)
        .where(Metric.recorded_at >= threshold)
    )
    return int(session.scalar(stmt) or 0)
