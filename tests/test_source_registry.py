from __future__ import annotations

from pathlib import Path

import pytest

from src.source_registry import SourceValidationError, load_source_file, validate_source_document


def test_load_source_file_accepts_valid_yaml(tmp_path: Path) -> None:
    source_path = tmp_path / "openai_blog.yaml"
    source_path.write_text(
        """
id: openai_blog
track: A
kind: rss
endpoint: https://openai.com/blog/rss.xml
license_class: first_party
trust: 0.9
auto_publish_allowed: false
language: en
topics: [llm]
fetch:
  interval: 6h
  etag: true
  timeout_sec: 30
  rate_limit: 60
extract:
  strategy: trafilatura
dedupe:
  key: canonical_url
  near_dup: simhash
post_rules:
  min_words: 400
  require_code_or_figure: false
enabled: true
""".strip(),
        encoding="utf-8",
    )

    document = load_source_file(source_path)

    assert document["id"] == "openai_blog"


def test_validate_source_document_rejects_missing_required_field() -> None:
    document = {
        "id": "openai_blog",
        "track": "A",
        "kind": "rss",
        "endpoint": "https://openai.com/blog/rss.xml",
        "license_class": "first_party",
        "trust": 0.9,
        "auto_publish_allowed": False,
        "language": "en",
        "topics": ["llm"],
        "fetch": {"interval": "6h", "etag": True, "timeout_sec": 30, "rate_limit": 60},
        "extract": {"strategy": "trafilatura"},
        "dedupe": {"key": "canonical_url", "near_dup": "simhash"},
        "enabled": True,
    }

    with pytest.raises(SourceValidationError, match="post_rules"):
        validate_source_document(document, source_name="openai_blog.yaml")


def test_load_source_file_rejects_filename_id_mismatch(tmp_path: Path) -> None:
    source_path = tmp_path / "openai_blog.yaml"
    source_path.write_text(
        """
id: different_id
track: A
kind: rss
endpoint: https://openai.com/blog/rss.xml
license_class: first_party
trust: 0.9
auto_publish_allowed: false
language: en
topics: [llm]
fetch:
  interval: 6h
  etag: true
  timeout_sec: 30
  rate_limit: 60
extract:
  strategy: trafilatura
dedupe:
  key: canonical_url
  near_dup: simhash
post_rules:
  min_words: 400
  require_code_or_figure: false
enabled: true
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(SourceValidationError, match="filename stem"):
        load_source_file(source_path)
