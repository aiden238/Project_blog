from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.config import settings


def append_json_log(relative_path: str | Path, payload: dict[str, Any]) -> None:
    path = settings.resolved_logs_dir / Path(relative_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
