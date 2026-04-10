from datetime import datetime, timezone

from src.storage import build_stage_path, extension_from_content_type


def test_extension_from_content_type_uses_known_mapping() -> None:
    assert extension_from_content_type("text/html; charset=utf-8") == "html"


def test_build_stage_path_uses_phase_layout_naming_rule() -> None:
    path = build_stage_path(
        "raw",
        "openai_blog",
        file_hash="a1b2c3d4e5f6",
        extension="html",
        timestamp=datetime(2026, 4, 20, 12, 34, 56, tzinfo=timezone.utc),
    )

    assert path.name == "2026-04-20T12-34-56Z_openai_blog_a1b2c3d4e5f6.html"
    assert path.parent.name == "openai_blog"
