from src.prompting import load_prompt_template, render_prompt


def test_load_prompt_template_uses_latest_version() -> None:
    template = load_prompt_template("draft")

    assert template.version == 1
    assert template.version_id == "draft_v1"


def test_render_prompt_applies_context() -> None:
    template = render_prompt(
        "summary",
        {
            "title": "Example",
            "body": "Body text",
        },
    )

    assert "Example" in template.body
    assert "Body text" in template.body
