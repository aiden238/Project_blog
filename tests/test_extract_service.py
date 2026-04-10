from src.extract.service import ExtractedContent, extract_html_content


def test_extract_html_content_uses_custom_parser_when_primary_extractor_fails(monkeypatch) -> None:
    monkeypatch.setattr("src.extract.service.trafilatura.extract", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "src.extract.service.load_custom_parser",
        lambda source_id: (lambda html, url: ExtractedContent("custom text", 1, 0, {"strategy": "custom"})),
    )

    extracted = extract_html_content("openai_blog", "https://example.com/post", "<html><body></body></html>")

    assert extracted.text == "custom text"
    assert extracted.meta["strategy"] == "custom"
