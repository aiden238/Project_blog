from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import timedelta
from typing import Any
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import feedparser
import httpx
from sqlalchemy.orm import Session

from src.config import settings
from src.logging_utils import append_json_log
from src.metrics import count_metrics_in_window, record_metric
from src.models import Source

DEFAULT_STATE_KEY = "__default__"
HTTP_TIMEOUT = settings.fetch_timeout_sec

_HTTP_CLIENT: httpx.Client | None = None


@dataclass(frozen=True)
class HttpFetchResult:
    response: httpx.Response | None
    not_modified: bool
    skipped: bool
    skip_reason: str | None


def get_http_client() -> httpx.Client:
    global _HTTP_CLIENT
    if _HTTP_CLIENT is None:
        _HTTP_CLIENT = httpx.Client(
            follow_redirects=True,
            timeout=HTTP_TIMEOUT,
            headers={"User-Agent": settings.fetch_user_agent},
        )
    return _HTTP_CLIENT


def parse_feed_document(content: bytes) -> Any:
    return feedparser.parse(content)


class RobotsPolicy:
    def __init__(self, client: httpx.Client | None = None) -> None:
        self.client = client or get_http_client()
        self._cache: dict[str, RobotFileParser | None] = {}

    def can_fetch(self, url: str) -> bool:
        split = urlsplit(url)
        origin = f"{split.scheme}://{split.netloc}"
        parser = self._cache.get(origin)
        if parser is None and origin not in self._cache:
            parser = self._fetch_parser(origin)
            self._cache[origin] = parser

        if parser is None:
            append_json_log(
                "robots/violations.log",
                {"url": url, "reason": "robots_unavailable"},
            )
            return False

        allowed = parser.can_fetch(settings.fetch_user_agent, url)
        if not allowed:
            append_json_log(
                "robots/violations.log",
                {"url": url, "reason": "disallow"},
            )
        return allowed

    def _fetch_parser(self, origin: str) -> RobotFileParser | None:
        robots_url = f"{origin}/robots.txt"
        try:
            response = self.client.get(robots_url, timeout=HTTP_TIMEOUT)
        except httpx.HTTPError:
            return None

        parser = RobotFileParser()
        parser.set_url(robots_url)

        if response.status_code == 404:
            parser.parse([])
            return parser

        if response.is_success:
            parser.parse(response.text.splitlines())
            return parser

        return None


def enforce_rate_limit(session: Session, source: Source) -> bool:
    configured_limit = int(
        source.fetch_config.get("rate_limit", settings.fetch_rate_limit_per_hour)
    )
    recent_count = count_metrics_in_window(
        session,
        kind="fetch",
        target_id=source.id,
        window=timedelta(hours=1),
    )
    if recent_count < configured_limit:
        return True

    append_json_log(
        "fetch/rate_limit.log",
        {
            "source_id": source.id,
            "configured_limit": configured_limit,
            "recent_count": recent_count,
        },
    )
    return False


def request_with_retries(
    session: Session,
    source: Source,
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    state_key: str | None = None,
    use_conditional_headers: bool = False,
    client: httpx.Client | None = None,
    sleep_fn=time.sleep,
) -> HttpFetchResult:
    http_client = client or get_http_client()
    request_headers = dict(headers or {})
    if use_conditional_headers:
        request_headers.update(build_conditional_headers(source, state_key=state_key))

    for attempt in range(settings.fetch_max_retries):
        try:
            response = http_client.request(
                method,
                url,
                headers=request_headers,
                timeout=settings.fetch_timeout_sec,
            )
            source.fetch_count = int(source.fetch_count or 0) + 1

            if response.status_code == 304:
                record_metric(
                    session,
                    kind="fetch",
                    target_id=source.id,
                    value=1.0,
                    meta={
                        "url": url,
                        "status_code": 304,
                        "not_modified": True,
                    },
                )
                return HttpFetchResult(
                    response=response,
                    not_modified=True,
                    skipped=True,
                    skip_reason="not_modified",
                )

            if response.status_code == 429 or response.status_code >= 500:
                if attempt == settings.fetch_max_retries - 1:
                    record_metric(
                        session,
                        kind="fetch",
                        target_id=source.id,
                        value=0.0,
                        meta={"url": url, "status_code": response.status_code},
                    )
                    response.raise_for_status()
                sleep_fn(2**attempt)
                continue

            record_metric(
                session,
                kind="fetch",
                target_id=source.id,
                value=1.0 if response.is_success else 0.0,
                meta={"url": url, "status_code": response.status_code},
            )
            if response.is_success and use_conditional_headers:
                update_conditional_state(
                    source,
                    state_key=state_key,
                    etag=response.headers.get("ETag"),
                    last_modified=response.headers.get("Last-Modified"),
                )
            response.raise_for_status()
            return HttpFetchResult(
                response=response,
                not_modified=False,
                skipped=False,
                skip_reason=None,
            )
        except httpx.HTTPError as error:
            if attempt == settings.fetch_max_retries - 1:
                record_metric(
                    session,
                    kind="fetch",
                    target_id=source.id,
                    value=0.0,
                    meta={"url": url, "error": str(error)},
                )
                raise
            sleep_fn(2**attempt)

    return HttpFetchResult(response=None, not_modified=False, skipped=True, skip_reason="retry_exhausted")


def build_conditional_headers(source: Source, *, state_key: str | None = None) -> dict[str, str]:
    if not source.fetch_config.get("etag", True):
        return {}

    key = state_key or DEFAULT_STATE_KEY
    headers: dict[str, str] = {}
    etag = read_state_value(source.etag, key)
    last_modified = read_state_value(source.last_modified, key)
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified
    return headers


def update_conditional_state(
    source: Source,
    *,
    state_key: str | None,
    etag: str | None,
    last_modified: str | None,
) -> None:
    key = state_key or DEFAULT_STATE_KEY
    if etag is not None:
        state = decode_state_map(source.etag)
        state[key] = etag
        source.etag = encode_state_map(state)
    if last_modified is not None:
        state = decode_state_map(source.last_modified)
        state[key] = last_modified
        source.last_modified = encode_state_map(state)


def read_state_value(raw_value: str | None, key: str) -> str | None:
    state_map = decode_state_map(raw_value)
    return state_map.get(key)


def decode_state_map(raw_value: str | None) -> dict[str, str]:
    if not raw_value:
        return {}
    try:
        payload = json.loads(raw_value)
    except json.JSONDecodeError:
        return {DEFAULT_STATE_KEY: raw_value}
    if isinstance(payload, dict):
        return {str(key): str(value) for key, value in payload.items()}
    return {DEFAULT_STATE_KEY: raw_value}


def encode_state_map(state_map: dict[str, str]) -> str | None:
    if not state_map:
        return None
    if set(state_map) == {DEFAULT_STATE_KEY}:
        return state_map[DEFAULT_STATE_KEY]
    return json.dumps(state_map, sort_keys=True)
