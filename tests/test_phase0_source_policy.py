from __future__ import annotations

from pathlib import Path

from src.source_registry import load_source_documents


def test_phase0_source_policy_matches_foundation_constraints() -> None:
    documents = load_source_documents(Path("sources"))

    assert len(documents) == 3
    assert {document["id"] for document in documents} == {
        "anthropic_news",
        "github_releases_llm",
        "openai_blog",
    }

    for document in documents:
        assert document["track"] == "A"
        assert document["license_class"] == "first_party"
        assert document["auto_publish_allowed"] is False
