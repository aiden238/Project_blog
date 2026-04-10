from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import httpx

from src.collection import CandidateDocument, CollectionResult, CollectionService
from src.extract import ExtractedContent
from src.fetchers import HttpFetchResult
from src.models import Item, ReviewQueue, Source


class FakeExecuteResult:
    def __init__(self, rows: list[tuple[Any, ...]]) -> None:
        self._rows = rows

    def __iter__(self):
        return iter(self._rows)


class FakeSession:
    def __init__(
        self,
        *,
        scalar_result: str | None = None,
        execute_rows: list[tuple[Any, ...]] | None = None,
    ) -> None:
        self.scalar_result = scalar_result
        self.execute_rows = execute_rows or []
        self.added: list[object] = []
        self.flushed = 0

    def scalar(self, _statement: object) -> str | None:
        return self.scalar_result

    def execute(self, _statement: object) -> FakeExecuteResult:
        return FakeExecuteResult(self.execute_rows)

    def add(self, obj: object) -> None:
        self.added.append(obj)

    def flush(self) -> None:
        self.flushed += 1
        for index, obj in enumerate(self.added, start=1):
            if getattr(obj, "id", None) is None:
                setattr(obj, "id", f"generated-{index}")


def build_source() -> Source:
    return Source(
        id="openai_blog",
        track="A",
        kind="rss",
        endpoint="https://example.com/feed.xml",
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


def test_process_candidate_skips_existing_canonical_duplicate(monkeypatch) -> None:
    session = FakeSession(scalar_result="item-1")
    service = CollectionService(session)
    result = CollectionResult()
    duplicate_logs: list[dict[str, Any]] = []
    monkeypatch.setattr(
        "src.collection.append_json_log",
        lambda _path, payload: duplicate_logs.append(payload),
    )

    candidate = CandidateDocument(
        source_id="openai_blog",
        canonical_url="https://example.com/post",
        title="Example",
        external_id="external-1",
        raw_bytes=b"<html></html>",
        content_type="text/html",
        origin_url="https://example.com/post",
        pre_extracted=ExtractedContent("long enough body", 1, 0, {"strategy": "test"}),
    )

    service._process_candidate(build_source(), candidate, result=result, dry_run=False)

    assert result.duplicates_skipped == 1
    assert session.added == []
    assert duplicate_logs[0]["reason"] == "canonical_url"


def test_process_candidate_marks_extract_failed_and_records_metric(monkeypatch) -> None:
    session = FakeSession()
    service = CollectionService(session)
    result = CollectionResult()
    recorded_metrics: list[dict[str, Any]] = []
    monkeypatch.setattr(
        service,
        "_persist_raw_artifact",
        lambda *args, **kwargs: "/tmp/raw.html",
    )
    monkeypatch.setattr(
        "src.collection.record_metric",
        lambda _session, **kwargs: recorded_metrics.append(kwargs),
    )

    candidate = CandidateDocument(
        source_id="openai_blog",
        canonical_url="https://example.com/post",
        title="Example",
        external_id="external-1",
        raw_bytes=b"<html></html>",
        content_type="text/html",
        origin_url="https://example.com/post",
        pre_extracted=ExtractedContent("", 0, 0, {"strategy": "test"}),
    )

    service._process_candidate(build_source(), candidate, result=result, dry_run=False)

    assert result.extract_failed == 1
    assert len(session.added) == 1
    item = session.added[0]
    assert isinstance(item, Item)
    assert item.status == "extract_failed"
    assert item.raw_path == "/tmp/raw.html"
    assert recorded_metrics[0]["kind"] == "extract"
    assert recorded_metrics[0]["meta"]["failed"] is True


def test_process_candidate_flags_suspicious_item_and_creates_review_queue(monkeypatch) -> None:
    session = FakeSession()
    service = CollectionService(session)
    result = CollectionResult()
    recorded_metrics: list[dict[str, Any]] = []
    monkeypatch.setattr(
        service,
        "_persist_raw_artifact",
        lambda *args, **kwargs: "/tmp/raw.html",
    )
    monkeypatch.setattr(
        service,
        "_persist_clean_artifact",
        lambda *args, **kwargs: "/tmp/clean.json",
    )
    monkeypatch.setattr(
        "src.collection.record_metric",
        lambda _session, **kwargs: recorded_metrics.append(kwargs),
    )

    candidate = CandidateDocument(
        source_id="openai_blog",
        canonical_url="https://example.com/post",
        title="Example",
        external_id="external-1",
        raw_bytes=b"<html></html>",
        content_type="text/html",
        origin_url="https://example.com/post",
        pre_extracted=ExtractedContent("short body", 1, 0, {"strategy": "test"}),
    )

    service._process_candidate(build_source(), candidate, result=result, dry_run=False)

    assert result.items_written == 1
    assert result.suspicious_items == 1
    assert len(session.added) == 2
    item, review_queue = session.added
    assert isinstance(item, Item)
    assert item.status == "clean"
    assert item.clean_path == "/tmp/clean.json"
    assert item.item_meta["flags"] == ["extract_suspicious"]
    assert isinstance(review_queue, ReviewQueue)
    assert review_queue.reason == "extract_suspicious"
    assert recorded_metrics[0]["meta"]["suspicious"] is True


def test_process_candidate_skips_near_duplicate_by_simhash(monkeypatch) -> None:
    session = FakeSession(execute_rows=[("item-2", "abcd1234abcd1234")])
    service = CollectionService(session)
    result = CollectionResult()
    duplicate_logs: list[dict[str, Any]] = []
    monkeypatch.setattr(
        "src.collection.append_json_log",
        lambda _path, payload: duplicate_logs.append(payload),
    )
    monkeypatch.setattr("src.collection.compute_simhash64", lambda _text: "abcd1234abcd1234")
    monkeypatch.setattr("src.collection.hamming_distance", lambda _left, _right: 0)

    candidate = CandidateDocument(
        source_id="openai_blog",
        canonical_url="https://example.com/post",
        title="Example",
        external_id="external-1",
        raw_bytes=b"<html></html>",
        content_type="text/html",
        origin_url="https://example.com/post",
        pre_extracted=ExtractedContent(
            "This body is long enough to avoid suspicious handling.",
            1,
            0,
            {"strategy": "test"},
        ),
    )

    service._process_candidate(build_source(), candidate, result=result, dry_run=False)

    assert result.duplicates_skipped == 1
    assert session.added == []
    assert duplicate_logs[0]["reason"] == "simhash"


def test_fetch_rss_candidates_falls_back_to_feed_summary_when_article_fetch_fails(monkeypatch) -> None:
    session = FakeSession()
    robots = SimpleNamespace(can_fetch=lambda _url: True)
    service = CollectionService(session, robots_policy=robots)
    source = build_source()

    feed_entry = SimpleNamespace(
        link="https://example.com/post",
        title="Example",
        id="external-1",
        summary="<p>Feed fallback body with enough detail to keep the item useful.</p>",
    )

    def fake_request_with_retries(_session, _source, url, **_kwargs):
        if url == source.endpoint:
            return HttpFetchResult(
                response=httpx.Response(
                    200,
                    request=httpx.Request("GET", url),
                    content=b"<rss />",
                ),
                not_modified=False,
                skipped=False,
                skip_reason=None,
            )
        raise httpx.HTTPError("forbidden")

    monkeypatch.setattr(
        "src.collection.request_with_retries",
        fake_request_with_retries,
    )
    monkeypatch.setattr(
        "src.collection.parse_feed_document",
        lambda _content: SimpleNamespace(entries=[feed_entry]),
    )

    candidates, not_modified, robots_blocked = service._fetch_rss_candidates(source, limit=1)

    assert not_modified == 0
    assert robots_blocked == 0
    assert len(candidates) == 1
    assert candidates[0].item_meta["feed_fallback"] is True
    assert candidates[0].pre_extracted is not None
    assert "Feed fallback body" in candidates[0].pre_extracted.text
