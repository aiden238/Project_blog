from __future__ import annotations

import httpx

from src.fetchers import get_http_client, request_with_retries
from src.models import Source


class FakeSession:
    def __init__(self) -> None:
        self.objects: list[object] = []

    def add(self, obj: object) -> None:
        self.objects.append(obj)


def test_http_client_is_singleton() -> None:
    assert get_http_client() is get_http_client()


def test_request_with_retries_marks_not_modified_and_increments_fetch_count() -> None:
    source = Source(
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
        etag='"etag-value"',
        last_modified="Wed, 01 Jan 2025 00:00:00 GMT",
        fetch_count=0,
    )
    session = FakeSession()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["If-None-Match"] == '"etag-value"'
        assert request.headers["If-Modified-Since"] == "Wed, 01 Jan 2025 00:00:00 GMT"
        return httpx.Response(304, request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = request_with_retries(
        session,
        source,
        source.endpoint,
        use_conditional_headers=True,
        client=client,
    )

    assert result.not_modified is True
    assert source.fetch_count == 1
    assert session.objects
