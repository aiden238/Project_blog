from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.dedupe import SIMHASH_HAMMING_THRESHOLD, compute_simhash64, hamming_distance
from src.extract import ExtractedContent, extract_html_content, extract_markdown_content
from src.fetchers import (
    RobotsPolicy,
    enforce_rate_limit,
    get_http_client,
    parse_feed_document,
    request_with_retries,
)
from src.logging_utils import append_json_log
from src.metrics import record_metric
from src.models import Item, ReviewQueue, Source
from src.storage import (
    build_stage_path,
    extension_from_content_type,
    short_hash,
    write_clean_document,
    write_raw_bytes,
)
from src.url_utils import normalize_url


@dataclass(frozen=True)
class CandidateDocument:
    source_id: str
    canonical_url: str
    title: str | None
    external_id: str | None
    raw_bytes: bytes
    content_type: str
    origin_url: str
    pre_extracted: ExtractedContent | None = None
    item_meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class CollectionResult:
    sources_processed: int = 0
    candidates_seen: int = 0
    items_written: int = 0
    duplicates_skipped: int = 0
    extract_failed: int = 0
    suspicious_items: int = 0
    not_modified: int = 0
    rate_limited: int = 0
    robots_blocked: int = 0


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CollectionService:
    def __init__(
        self,
        session: Session,
        *,
        robots_policy: RobotsPolicy | None = None,
    ) -> None:
        self.session = session
        self.client = get_http_client()
        self.robots = robots_policy or RobotsPolicy(self.client)

    def fetch_sources(
        self,
        *,
        source_id: str | None = None,
        limit: int | None = None,
        dry_run: bool = False,
    ) -> CollectionResult:
        result = CollectionResult()
        sources = self._load_sources(source_id)

        for source in sources:
            result.sources_processed += 1

            if not enforce_rate_limit(self.session, source):
                result.rate_limited += 1
                continue

            if source.kind == "rss":
                candidates, source_not_modified, source_robots_blocked = self._fetch_rss_candidates(
                    source,
                    limit=limit,
                )
            elif source.kind == "github_release":
                candidates, source_not_modified, source_robots_blocked = self._fetch_github_release_candidates(
                    source,
                    limit=limit,
                )
            else:
                continue

            result.not_modified += source_not_modified
            result.robots_blocked += source_robots_blocked

            for candidate in candidates:
                result.candidates_seen += 1
                self._process_candidate(source, candidate, result=result, dry_run=dry_run)

        return result

    def _load_sources(self, source_id: str | None) -> list[Source]:
        stmt = select(Source).where(Source.enabled.is_(True)).order_by(Source.id)
        if source_id:
            stmt = stmt.where(Source.id == source_id)
        return list(self.session.scalars(stmt))

    def _fetch_rss_candidates(
        self,
        source: Source,
        *,
        limit: int | None,
    ) -> tuple[list[CandidateDocument], int, int]:
        respect_robots = source.fetch_config.get("respect_robots", True)
        if respect_robots and not self.robots.can_fetch(source.endpoint):
            return [], 0, 1

        try:
            feed_response = request_with_retries(
                self.session,
                source,
                source.endpoint,
                use_conditional_headers=True,
                client=self.client,
            )
        except httpx.HTTPError:
            return [], 0, 0
        if feed_response.not_modified or feed_response.response is None:
            return [], 1, 0

        parsed = parse_feed_document(feed_response.response.content)
        entries = parsed.entries[: limit or len(parsed.entries)]
        candidates: list[CandidateDocument] = []
        robots_blocked = 0

        for entry in entries:
            raw_link = getattr(entry, "link", None)
            if not raw_link:
                continue
            article_url = normalize_url(raw_link)
            if respect_robots and not self.robots.can_fetch(article_url):
                robots_blocked += 1
                continue

            try:
                article_response = request_with_retries(
                    self.session,
                    source,
                    article_url,
                    client=self.client,
                )
            except httpx.HTTPError:
                fallback_candidate = self._build_feed_entry_fallback_candidate(
                    source,
                    entry,
                    article_url=article_url,
                    raw_link=raw_link,
                )
                if fallback_candidate is not None:
                    candidates.append(fallback_candidate)
                continue
            if article_response.response is None or article_response.skipped:
                fallback_candidate = self._build_feed_entry_fallback_candidate(
                    source,
                    entry,
                    article_url=article_url,
                    raw_link=raw_link,
                )
                if fallback_candidate is not None:
                    candidates.append(fallback_candidate)
                continue

            content_type = article_response.response.headers.get("Content-Type", "text/html")
            candidate = CandidateDocument(
                source_id=source.id,
                canonical_url=article_url,
                title=getattr(entry, "title", None),
                external_id=getattr(entry, "id", None) or raw_link,
                raw_bytes=article_response.response.content,
                content_type=content_type,
                origin_url=str(article_response.response.url),
                item_meta={"entry_link": raw_link},
            )
            candidates.append(candidate)

        return candidates, 0, robots_blocked

    def _build_feed_entry_fallback_candidate(
        self,
        source: Source,
        entry: Any,
        *,
        article_url: str,
        raw_link: str,
    ) -> CandidateDocument | None:
        markup = self._extract_feed_entry_markup(entry)
        if not markup:
            return None

        html_fragment = f"<html><body>{markup}</body></html>"
        extracted = extract_html_content(source.id, article_url, html_fragment)
        if not extracted.text.strip():
            return None

        return CandidateDocument(
            source_id=source.id,
            canonical_url=article_url,
            title=getattr(entry, "title", None),
            external_id=getattr(entry, "id", None) or raw_link,
            raw_bytes=html_fragment.encode("utf-8"),
            content_type="text/html",
            origin_url=article_url,
            pre_extracted=ExtractedContent(
                text=extracted.text,
                heading_count=extracted.heading_count,
                code_block_count=extracted.code_block_count,
                meta={**extracted.meta, "feed_fallback": True},
            ),
            item_meta={"entry_link": raw_link, "feed_fallback": True},
        )

    def _extract_feed_entry_markup(self, entry: Any) -> str | None:
        content_blocks = getattr(entry, "content", None)
        if content_blocks:
            first_block = content_blocks[0]
            if isinstance(first_block, dict):
                value = first_block.get("value")
            else:
                value = getattr(first_block, "value", None)
            if value and str(value).strip():
                return str(value)

        summary = getattr(entry, "summary", None)
        if summary and str(summary).strip():
            return str(summary)

        return None

    def _fetch_github_release_candidates(
        self,
        source: Source,
        *,
        limit: int | None,
    ) -> tuple[list[CandidateDocument], int, int]:
        repos = list(source.fetch_config.get("repos", []))
        candidates: list[CandidateDocument] = []
        not_modified = 0
        robots_blocked = 0

        for repo in repos[: limit or len(repos)]:
            request_url = source.endpoint.format(repo=repo)
            respect_robots = source.fetch_config.get("respect_robots", True)
            if respect_robots and not self.robots.can_fetch(request_url):
                robots_blocked += 1
                continue

            try:
                response = request_with_retries(
                    self.session,
                    source,
                    request_url,
                    state_key=repo,
                    use_conditional_headers=True,
                    client=self.client,
                    headers={"Accept": "application/vnd.github+json"},
                )
            except httpx.HTTPError:
                continue
            if response.not_modified:
                not_modified += 1
                continue
            if response.response is None or response.skipped:
                continue

            payload = response.response.json()
            canonical_url = normalize_url(payload.get("html_url") or str(response.response.url))
            extracted = extract_markdown_content(payload.get("body") or "")
            candidate = CandidateDocument(
                source_id=source.id,
                canonical_url=canonical_url,
                title=payload.get("name") or payload.get("tag_name"),
                external_id=str(payload.get("id")) if payload.get("id") is not None else repo,
                raw_bytes=response.response.content,
                content_type=response.response.headers.get("Content-Type", "application/json"),
                origin_url=str(response.response.url),
                pre_extracted=extracted,
                item_meta={"repo": repo, "tag_name": payload.get("tag_name")},
            )
            candidates.append(candidate)

        return candidates, not_modified, robots_blocked

    def _process_candidate(
        self,
        source: Source,
        candidate: CandidateDocument,
        *,
        result: CollectionResult,
        dry_run: bool,
    ) -> None:
        existing = self.session.scalar(
            select(Item.id).where(Item.canonical_url == candidate.canonical_url)
        )
        if existing:
            self._log_duplicate(
                source.id,
                candidate.canonical_url,
                reason="canonical_url",
                duplicate_of=str(existing),
            )
            result.duplicates_skipped += 1
            return

        extracted = candidate.pre_extracted
        if extracted is None:
            html = candidate.raw_bytes.decode("utf-8", errors="ignore")
            extracted = extract_html_content(source.id, candidate.origin_url, html)

        if not extracted.text.strip():
            result.extract_failed += 1
            if dry_run:
                return

            artifact_time = utcnow()
            artifact_hash = short_hash(candidate.raw_bytes)
            raw_path = self._persist_raw_artifact(
                source.id,
                candidate.raw_bytes,
                candidate.content_type,
                file_hash=artifact_hash,
                timestamp=artifact_time,
            )
            item = Item(
                source_id=source.id,
                track=source.track,
                license_class=source.license_class,
                canonical_url=candidate.canonical_url,
                external_id=candidate.external_id,
                title=candidate.title,
                status="extract_failed",
                raw_path=raw_path,
                item_meta={**candidate.item_meta, "origin_url": candidate.origin_url},
            )
            self.session.add(item)
            self.session.flush()
            record_metric(
                self.session,
                kind="extract",
                target_id=item.id,
                value=0.0,
                meta={"heading_count": 0, "code_block_count": 0, "failed": True},
            )
            return

        content_simhash = compute_simhash64(extracted.text)
        duplicate_item_id = self._find_simhash_duplicate(content_simhash)
        if duplicate_item_id is not None:
            self._log_duplicate(
                source.id,
                candidate.canonical_url,
                reason="simhash",
                duplicate_of=duplicate_item_id,
                simhash=content_simhash,
            )
            result.duplicates_skipped += 1
            return

        suspicious = len(extracted.text.strip()) < 50
        if dry_run:
            result.items_written += 1
            if suspicious:
                result.suspicious_items += 1
            return

        artifact_time = utcnow()
        file_hash = short_hash(candidate.raw_bytes)
        raw_path = self._persist_raw_artifact(
            source.id,
            candidate.raw_bytes,
            candidate.content_type,
            file_hash=file_hash,
            timestamp=artifact_time,
        )
        clean_path = self._persist_clean_artifact(
            source.id,
            file_hash=file_hash,
            timestamp=artifact_time,
            payload={
                "canonical_url": candidate.canonical_url,
                "title": candidate.title,
                "source_id": source.id,
                "origin_url": candidate.origin_url,
                "text": extracted.text,
                "heading_count": extracted.heading_count,
                "code_block_count": extracted.code_block_count,
                "meta": extracted.meta,
            },
        )

        flags = ["extract_suspicious"] if suspicious else []
        item = Item(
            source_id=source.id,
            track=source.track,
            license_class=source.license_class,
            canonical_url=candidate.canonical_url,
            external_id=candidate.external_id,
            title=candidate.title,
            status="clean",
            content_simhash=content_simhash,
            raw_path=raw_path,
            clean_path=clean_path,
            item_meta={
                **candidate.item_meta,
                "origin_url": candidate.origin_url,
                "flags": flags,
            },
        )
        self.session.add(item)
        self.session.flush()

        record_metric(
            self.session,
            kind="extract",
            target_id=item.id,
            value=float(len(extracted.text)),
            meta={
                "heading_count": extracted.heading_count,
                "code_block_count": extracted.code_block_count,
                "suspicious": suspicious,
            },
        )

        if suspicious:
            self.session.add(
                ReviewQueue(
                    item_id=item.id,
                    reason="extract_suspicious",
                    payload={"body_length": len(extracted.text)},
                )
            )
            result.suspicious_items += 1

        result.items_written += 1

    def _persist_raw_artifact(
        self,
        source_id: str,
        payload: bytes,
        content_type: str,
        *,
        file_hash: str | None = None,
        timestamp: datetime | None = None,
    ) -> str:
        artifact_hash = file_hash or short_hash(payload)
        extension = extension_from_content_type(content_type)
        path = build_stage_path(
            "raw",
            source_id,
            file_hash=artifact_hash,
            extension=extension,
            timestamp=timestamp or utcnow(),
        )
        return write_raw_bytes(path, payload)

    def _persist_clean_artifact(
        self,
        source_id: str,
        *,
        file_hash: str,
        timestamp: datetime | None = None,
        payload: dict[str, Any],
    ) -> str:
        path = build_stage_path(
            "clean",
            source_id,
            file_hash=file_hash,
            extension="json",
            timestamp=timestamp or utcnow(),
        )
        return write_clean_document(path, payload)

    def _find_simhash_duplicate(self, candidate_hash: str) -> str | None:
        stmt = select(Item.id, Item.content_simhash).where(Item.content_simhash.is_not(None))
        for item_id, existing_hash in self.session.execute(stmt):
            if existing_hash is None:
                continue
            if hamming_distance(existing_hash, candidate_hash) <= SIMHASH_HAMMING_THRESHOLD:
                return str(item_id)
        return None

    def _log_duplicate(
        self,
        source_id: str,
        canonical_url: str,
        *,
        reason: str,
        duplicate_of: str,
        simhash: str | None = None,
    ) -> None:
        append_json_log(
            "dedupe.log",
            {
                "source_id": source_id,
                "canonical_url": canonical_url,
                "reason": reason,
                "duplicate_of": duplicate_of,
                "simhash": simhash,
            },
        )


def render_collection_result(result: CollectionResult) -> str:
    payload = {
        "sources_processed": result.sources_processed,
        "candidates_seen": result.candidates_seen,
        "items_written": result.items_written,
        "duplicates_skipped": result.duplicates_skipped,
        "extract_failed": result.extract_failed,
        "suspicious_items": result.suspicious_items,
        "not_modified": result.not_modified,
        "rate_limited": result.rate_limited,
        "robots_blocked": result.robots_blocked,
    }
    return json.dumps(payload, indent=2)
