from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Any

from selectolax.parser import HTMLParser
import trafilatura


@dataclass(frozen=True)
class ExtractedContent:
    text: str
    heading_count: int
    code_block_count: int
    meta: dict[str, Any]


def extract_html_content(source_id: str, url: str, html: str) -> ExtractedContent:
    trafilatura_text = trafilatura.extract(html, url=url, output_format="txt")
    if trafilatura_text and trafilatura_text.strip():
        heading_count, code_block_count = count_html_structure(html)
        return ExtractedContent(
            text=trafilatura_text.strip(),
            heading_count=heading_count,
            code_block_count=code_block_count,
            meta={"strategy": "trafilatura"},
        )

    custom_parser = load_custom_parser(source_id)
    if custom_parser is not None:
        extracted = custom_parser(html, url)
        if isinstance(extracted, ExtractedContent) and extracted.text.strip():
            return extracted
        if isinstance(extracted, str) and extracted.strip():
            heading_count, code_block_count = count_html_structure(html)
            return ExtractedContent(
                text=extracted.strip(),
                heading_count=heading_count,
                code_block_count=code_block_count,
                meta={"strategy": f"custom_{source_id}"},
            )

    text, heading_count, code_block_count = fallback_extract_with_selectolax(html)
    return ExtractedContent(
        text=text,
        heading_count=heading_count,
        code_block_count=code_block_count,
        meta={"strategy": "selectolax"},
    )


def extract_markdown_content(markdown_text: str) -> ExtractedContent:
    lines = markdown_text.splitlines()
    heading_count = sum(1 for line in lines if line.lstrip().startswith("#"))
    code_block_count = markdown_text.count("```") // 2
    clean_lines = [line.strip("# ").rstrip() for line in lines if line.strip()]
    text = "\n".join(clean_lines).strip()
    return ExtractedContent(
        text=text,
        heading_count=heading_count,
        code_block_count=code_block_count,
        meta={"strategy": "markdown_body"},
    )


def load_custom_parser(source_id: str):
    module_name = f"src.extract.custom_{source_id}"
    try:
        module = import_module(module_name)
    except ModuleNotFoundError:
        return None
    return getattr(module, "extract", None)


def count_html_structure(html: str) -> tuple[int, int]:
    tree = HTMLParser(html)
    heading_count = sum(len(tree.css(selector)) for selector in ("h1", "h2", "h3", "h4", "h5", "h6"))
    code_block_count = len(tree.css("pre code")) or len(tree.css("code"))
    return heading_count, code_block_count


def fallback_extract_with_selectolax(html: str) -> tuple[str, int, int]:
    tree = HTMLParser(html)
    selectors = (
        "article",
        "main",
        "[role='main']",
        ".post-content",
        ".article-content",
        "body",
    )
    for selector in selectors:
        nodes = tree.css(selector)
        if not nodes:
            continue
        text = "\n".join(node.text(separator="\n").strip() for node in nodes).strip()
        if text:
            heading_count, code_block_count = count_html_structure(html)
            return text, heading_count, code_block_count

    return "", 0, 0
