from __future__ import annotations

from datetime import datetime, timezone

from src.models import Metric, Source
from src.reporting import build_fetch_health_report, render_fetch_health_report


class FakeScalarResult:
    def __init__(self, values):
        self._values = values

    def __iter__(self):
        return iter(self._values)


class FakeSession:
    def __init__(self, sources: list[Source], metrics: list[Metric]) -> None:
        self.sources = sources
        self.metrics = metrics
        self.calls = 0

    def scalars(self, _statement: object):
        self.calls += 1
        return FakeScalarResult(self.sources if self.calls == 1 else self.metrics)


def build_source(source_id: str) -> Source:
    return Source(
        id=source_id,
        track="A",
        kind="rss",
        endpoint=f"https://example.com/{source_id}.xml",
        license_class="first_party",
        trust=0.9,
        auto_publish_allowed=False,
        language="en",
        topics=["llm"],
        fetch_config={"etag": True, "rate_limit": 60},
        extract_config={"strategy": "trafilatura"},
        dedupe_config={"key": "canonical_url", "near_dup": "simhash"},
        post_rules={"min_words": 100, "require_code_or_figure": False},
        enabled=True,
        config_hash="0" * 64,
        fetch_count=0,
    )


def build_metric(target_id: str, value: float) -> Metric:
    return Metric(
        kind="fetch",
        target_id=target_id,
        value=value,
        meta={},
        recorded_at=datetime(2026, 4, 26, tzinfo=timezone.utc),
    )


def test_render_fetch_health_report_adds_disable_proposal_when_failure_rate_is_high() -> None:
    sources = [build_source("openai_blog")]
    metrics = [
        build_metric("openai_blog", 0.0),
        build_metric("openai_blog", 0.0),
        build_metric("openai_blog", 1.0),
    ]

    report = render_fetch_health_report(sources, metrics)

    assert "failure_rate=0.67" in report
    assert "disable_proposal" in report


def test_build_fetch_health_report_reads_sources_and_metrics_from_session() -> None:
    session = FakeSession(
        sources=[build_source("openai_blog"), build_source("anthropic_news")],
        metrics=[build_metric("openai_blog", 1.0), build_metric("anthropic_news", 0.0)],
    )

    report = build_fetch_health_report(session)

    assert "`openai_blog`" in report
    assert "`anthropic_news`" in report
