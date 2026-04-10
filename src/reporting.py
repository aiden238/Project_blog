from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models import Metric, Source

FETCH_HEALTH_WINDOW = timedelta(days=7)
FETCH_DISABLE_PROPOSAL_THRESHOLD = 0.5


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def load_fetch_health_data(
    session: Session,
    *,
    now: datetime | None = None,
    window: timedelta = FETCH_HEALTH_WINDOW,
) -> tuple[list[Source], list[Metric]]:
    threshold = (now or utcnow()) - window
    sources = list(session.scalars(select(Source).order_by(Source.id)))
    metrics = list(
        session.scalars(
            select(Metric)
            .where(Metric.kind == "fetch")
            .where(Metric.recorded_at >= threshold)
            .order_by(Metric.target_id, Metric.recorded_at)
        )
    )
    return sources, metrics


def render_fetch_health_report(
    sources: list[Source],
    metrics: list[Metric],
    *,
    failure_threshold: float = FETCH_DISABLE_PROPOSAL_THRESHOLD,
) -> str:
    grouped: dict[str, list[Metric]] = defaultdict(list)
    for metric in metrics:
        if metric.target_id:
            grouped[metric.target_id].append(metric)

    lines = ["# Fetch Health", ""]
    for source in sources:
        source_metrics = grouped.get(source.id, [])
        total = len(source_metrics)
        failures = sum(1 for metric in source_metrics if metric.value < 1.0)
        failure_rate = (failures / total) if total else 0.0
        lines.append(
            f"- `{source.id}`: total={total}, failures={failures}, failure_rate={failure_rate:.2f}"
        )
        if failure_rate > failure_threshold:
            lines.append(
                f"  disable_proposal: `{source.id}` exceeds 7-day failure rate "
                f"{failure_threshold:.2f}"
            )

    return "\n".join(lines)


def build_fetch_health_report(
    session: Session,
    *,
    now: datetime | None = None,
    window: timedelta = FETCH_HEALTH_WINDOW,
    failure_threshold: float = FETCH_DISABLE_PROPOSAL_THRESHOLD,
) -> str:
    sources, metrics = load_fetch_health_data(session, now=now, window=window)
    return render_fetch_health_report(
        sources,
        metrics,
        failure_threshold=failure_threshold,
    )
