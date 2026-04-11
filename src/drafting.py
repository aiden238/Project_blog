from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.llm import OllamaClient, OllamaClientError
from src.logging_utils import append_json_log
from src.metrics import record_metric
from src.models import Item, Outbox
from src.notion_projection import build_notion_projection_payload
from src.prompting import render_prompt
from src.storage import build_stage_path, short_hash, write_text_document


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class DraftGenerationResult:
    items_seen: int = 0
    drafts_written: int = 0
    llm_failed: int = 0
    outbox_enqueued: int = 0


class DraftService:
    def __init__(
        self,
        session: Session,
        *,
        llm_client: OllamaClient | None = None,
    ) -> None:
        self.session = session
        self.llm = llm_client or OllamaClient()

    def generate_drafts(
        self,
        *,
        source_id: str | None = None,
        limit: int | None = None,
        dry_run: bool = False,
    ) -> DraftGenerationResult:
        result = DraftGenerationResult()
        items = self._load_ready_items(source_id=source_id, limit=limit)

        for item in items:
            result.items_seen += 1
            clean_document = self._load_clean_document(item)
            prompt = render_prompt(
                "draft",
                {
                    "title": item.title or "",
                    "source_id": item.source_id,
                    "canonical_url": item.canonical_url,
                    "track": item.track,
                    "body": clean_document.get("text", ""),
                },
            )

            if dry_run:
                result.drafts_written += 1
                result.outbox_enqueued += 1
                continue

            try:
                completion = self.llm.generate(prompt.body)
            except OllamaClientError as error:
                self._mark_llm_failed(item, prompt_version=prompt.version_id, error=error)
                result.llm_failed += 1
                continue

            draft_path = self._persist_draft_artifact(
                item=item,
                content=completion.text,
            )
            item.status = "draft_ready"
            item.draft_path = draft_path
            item.item_meta = {
                **(item.item_meta or {}),
                "prompt_version": prompt.version_id,
                "draft_model": completion.model,
            }
            self._enqueue_notion_projection(
                item,
                draft_path=draft_path,
                draft_text=completion.text,
            )
            self._record_llm_metric(item, completion, prompt.version_id)
            self._record_draft_metric(
                item,
                completion.text,
                clean_document,
                prompt.version_id,
            )
            result.drafts_written += 1
            result.outbox_enqueued += 1

        return result

    def _load_ready_items(self, *, source_id: str | None, limit: int | None) -> list[Item]:
        stmt = (
            select(Item)
            .where(Item.status == "clean")
            .where(Item.track == "A")
            .order_by(Item.discovered_at, Item.id)
        )
        if source_id:
            stmt = stmt.where(Item.source_id == source_id)
        if limit:
            stmt = stmt.limit(limit)
        return list(self.session.scalars(stmt))

    def _load_clean_document(self, item: Item) -> dict[str, Any]:
        if not item.clean_path:
            raise FileNotFoundError(f"item {item.id} does not have clean_path")
        path = Path(item.clean_path)
        return json.loads(path.read_text(encoding="utf-8"))

    def _persist_draft_artifact(self, *, item: Item, content: str) -> str:
        path = build_stage_path(
            "drafts/track_a",
            item.source_id,
            file_hash=short_hash(content),
            extension="md",
            timestamp=utcnow(),
        )
        return write_text_document(path, content)

    def _enqueue_notion_projection(self, item: Item, *, draft_path: str, draft_text: str) -> None:
        summary = draft_text.strip().replace("\r", " ").replace("\n", " ")
        self.session.add(
            Outbox(
                target="notion",
                item_id=item.id,
                event_type="draft_ready",
                payload=build_notion_projection_payload(
                    {
                        "title": item.title,
                        "source_id": item.source_id,
                        "track": item.track,
                        "status": item.status,
                        "score": item.score,
                        "tags": [],
                        "license_class": item.license_class,
                        "localfs_path": draft_path,
                        "draft_url": None,
                        "summary": summary,
                    }
                ),
            )
        )

    def _mark_llm_failed(
        self,
        item: Item,
        *,
        prompt_version: str,
        error: Exception,
    ) -> None:
        item.status = "llm_failed"
        item.item_meta = {
            **(item.item_meta or {}),
            "prompt_version": prompt_version,
            "llm_error": str(error),
        }
        record_metric(
            self.session,
            kind="llm",
            target_id=item.id,
            value=0.0,
            meta={"failed": True, "prompt_version": prompt_version},
        )
        append_json_log(
            "llm/failures.log",
            {
                "item_id": item.id,
                "source_id": item.source_id,
                "prompt_version": prompt_version,
                "error": str(error),
            },
        )

    def _record_llm_metric(
        self,
        item: Item,
        completion,
        prompt_version: str,
    ) -> None:
        record_metric(
            self.session,
            kind="llm",
            target_id=item.id,
            value=completion.wall_time_sec,
            meta={
                "model": completion.model,
                "prompt_tokens": completion.prompt_tokens,
                "completion_tokens": completion.completion_tokens,
                "prompt_version": prompt_version,
                "failed": False,
            },
        )

    def _record_draft_metric(
        self,
        item: Item,
        draft_text: str,
        clean_document: dict[str, Any],
        prompt_version: str,
    ) -> None:
        clean_text = str(clean_document.get("text", ""))
        code_block_count = draft_text.count("```") // 2
        title_match = (
            1.0
            if item.title and item.title.lower() in draft_text.lower()
            else 0.0
        )
        compression_ratio = len(draft_text) / max(len(clean_text), 1)
        record_metric(
            self.session,
            kind="draft",
            target_id=item.id,
            value=float(len(draft_text)),
            meta={
                "code_block_count": code_block_count,
                "title_match": title_match,
                "compression_ratio": compression_ratio,
                "prompt_version": prompt_version,
            },
        )
