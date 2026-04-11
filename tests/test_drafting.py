from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from src.drafting import DraftService
from src.models import Item, Outbox


class FakeScalarResult:
    def __init__(self, values):
        self._values = values

    def __iter__(self):
        return iter(self._values)


class FakeSession:
    def __init__(self, items: list[Item]) -> None:
        self.items = items
        self.added: list[object] = []

    def scalars(self, _statement: object):
        return FakeScalarResult(self.items)

    def add(self, obj: object) -> None:
        self.added.append(obj)


class FakeCompletion:
    def __init__(self, text: str) -> None:
        self.text = text
        self.model = "gemma3:12b"
        self.prompt_tokens = 10
        self.completion_tokens = 20
        self.wall_time_sec = 1.2


class FakeOllamaClient:
    def __init__(self, *, should_fail: bool = False) -> None:
        self.should_fail = should_fail

    def generate(self, _prompt: str):
        if self.should_fail:
            from src.llm import OllamaClientError

            raise OllamaClientError("boom")
        return FakeCompletion("# Draft\n\nBody")


def build_item(tmp_path: Path) -> Item:
    clean_path = tmp_path / "clean.json"
    clean_path.write_text(
        '{"text": "Useful clean body", "canonical_url": "https://example.com/post"}',
        encoding="utf-8",
    )
    return Item(
        id="item-1",
        source_id="openai_blog",
        track="A",
        license_class="first_party",
        canonical_url="https://example.com/post",
        title="Example title",
        status="clean",
        clean_path=str(clean_path),
        item_meta={},
        discovered_at=datetime(2026, 4, 26, tzinfo=timezone.utc),
    )


def test_generate_drafts_marks_item_ready_and_enqueues_outbox(tmp_path: Path, monkeypatch) -> None:
    item = build_item(tmp_path)
    session = FakeSession([item])
    service = DraftService(session, llm_client=FakeOllamaClient())
    recorded_metrics: list[dict] = []
    monkeypatch.setattr(
        "src.drafting.record_metric",
        lambda _session, **kwargs: recorded_metrics.append(kwargs),
    )

    result = service.generate_drafts()

    assert result.drafts_written == 1
    assert result.outbox_enqueued == 1
    assert item.status == "draft_ready"
    assert item.draft_path is not None
    assert item.item_meta["prompt_version"] == "draft_v1"
    assert any(isinstance(obj, Outbox) for obj in session.added)
    assert {metric["kind"] for metric in recorded_metrics} == {"llm", "draft"}


def test_generate_drafts_marks_llm_failure(tmp_path: Path, monkeypatch) -> None:
    item = build_item(tmp_path)
    session = FakeSession([item])
    service = DraftService(session, llm_client=FakeOllamaClient(should_fail=True))
    recorded_metrics: list[dict] = []
    logged_failures: list[dict] = []
    monkeypatch.setattr(
        "src.drafting.record_metric",
        lambda _session, **kwargs: recorded_metrics.append(kwargs),
    )
    monkeypatch.setattr(
        "src.drafting.append_json_log",
        lambda _path, payload: logged_failures.append(payload),
    )

    result = service.generate_drafts()

    assert result.llm_failed == 1
    assert item.status == "llm_failed"
    assert item.item_meta["prompt_version"] == "draft_v1"
    assert recorded_metrics[0]["kind"] == "llm"
    assert recorded_metrics[0]["meta"]["failed"] is True
    assert logged_failures[0]["item_id"] == "item-1"
