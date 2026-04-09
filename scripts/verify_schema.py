from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import inspect

from src.config import settings
from src.db import create_db_engine

REQUIRED_TABLES = {"sources", "items", "outbox", "metrics"}
REQUIRED_COLUMNS = {
    "sources": {
        "id",
        "track",
        "kind",
        "endpoint",
        "license_class",
        "trust",
        "auto_publish_allowed",
        "language",
        "topics",
        "fetch_config",
        "extract_config",
        "dedupe_config",
        "post_rules",
        "enabled",
        "config_hash",
        "synced_at",
        "created_at",
        "updated_at",
    },
    "items": {
        "id",
        "source_id",
        "track",
        "license_class",
        "canonical_url",
        "status",
        "item_meta",
        "created_at",
        "updated_at",
    },
    "outbox": {
        "id",
        "target",
        "item_id",
        "event_type",
        "payload",
        "status",
        "attempts",
        "available_at",
        "created_at",
        "updated_at",
    },
    "metrics": {"id", "kind", "target_id", "value", "meta", "recorded_at"},
}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def ensure_log_dir() -> Path:
    log_dir = settings.resolved_logs_dir / "alembic"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def has_unique_on(inspector: Any, table_name: str, column_name: str) -> bool:
    unique_constraints = inspector.get_unique_constraints(table_name)
    if any(constraint["column_names"] == [column_name] for constraint in unique_constraints):
        return True

    indexes = inspector.get_indexes(table_name)
    return any(index["unique"] and index["column_names"] == [column_name] for index in indexes)


def has_index_on(inspector: Any, table_name: str, columns: list[str]) -> bool:
    indexes = inspector.get_indexes(table_name)
    return any(index["column_names"] == columns for index in indexes)


def verify_schema() -> list[str]:
    engine = create_db_engine()
    inspector = inspect(engine)
    errors: list[str] = []

    tables = set(inspector.get_table_names())
    missing_tables = sorted(REQUIRED_TABLES - tables)
    if missing_tables:
        errors.append(f"missing tables: {', '.join(missing_tables)}")
        return errors

    for table_name, required_columns in REQUIRED_COLUMNS.items():
        columns = {column["name"] for column in inspector.get_columns(table_name)}
        missing_columns = sorted(required_columns - columns)
        if missing_columns:
            errors.append(f"{table_name}: missing columns: {', '.join(missing_columns)}")

    if not has_unique_on(inspector, "items", "canonical_url"):
        errors.append("items: missing UNIQUE constraint/index on canonical_url")

    if not has_index_on(inspector, "outbox", ["status"]):
        errors.append("outbox: missing index on status")

    if not has_index_on(inspector, "metrics", ["kind", "recorded_at"]):
        errors.append("metrics: missing index on (kind, recorded_at)")

    engine.dispose()
    return errors


def append_log(status: str, errors: list[str]) -> None:
    log_entry = {
        "checked_at": utcnow().isoformat(),
        "status": status,
        "errors": errors,
    }
    log_file = ensure_log_dir() / "verify_schema.log"
    with log_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(log_entry, ensure_ascii=False) + "\n")


def main() -> int:
    errors = verify_schema()
    status = "ok" if not errors else "failed"
    append_log(status, errors)

    if errors:
        print("verify_schema FAILED:")
        for error in errors:
            print(f"  {error}")
        return 1

    print("verify_schema OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
