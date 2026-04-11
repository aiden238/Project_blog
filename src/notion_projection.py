from __future__ import annotations

from typing import Any


def build_notion_projection_payload(payload: dict[str, Any]) -> dict[str, Any]:
    summary = str(payload.get("summary", "")).strip().replace("\r", " ").replace("\n", " ")
    return {
        **payload,
        "summary": summary[:250],
    }
