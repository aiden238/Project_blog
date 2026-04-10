from __future__ import annotations

import hashlib
import json
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import settings

MIME_TO_EXTENSION = {
    "application/atom+xml": "xml",
    "application/json": "json",
    "application/rss+xml": "xml",
    "application/xml": "xml",
    "text/html": "html",
    "text/plain": "txt",
    "text/xml": "xml",
}


def utc_iso_timestamp(moment: datetime | None = None) -> str:
    value = (moment or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return value.strftime("%Y-%m-%dT%H-%M-%SZ")


def short_hash(content: bytes | str, *, length: int = 12) -> str:
    raw = content.encode("utf-8") if isinstance(content, str) else content
    return hashlib.sha256(raw).hexdigest()[:length]


def extension_from_content_type(content_type: str | None) -> str:
    if not content_type:
        return "bin"
    normalized = content_type.split(";")[0].strip().lower()
    return MIME_TO_EXTENSION.get(normalized, "bin")


def build_stage_path(
    stage: str,
    source_id: str,
    *,
    file_hash: str,
    extension: str,
    timestamp: datetime | None = None,
) -> Path:
    directory = settings.resolved_data_dir / stage / source_id
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{utc_iso_timestamp(timestamp)}_{source_id}_{file_hash}.{extension}"
    return directory / filename


def write_raw_bytes(path: Path, payload: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    current_mode = path.stat().st_mode
    path.chmod(current_mode & ~stat.S_IWRITE)
    return str(path.resolve())


def write_clean_document(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    return str(path.resolve())
