from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from src.models import Source

SOURCE_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "id",
        "track",
        "kind",
        "endpoint",
        "license_class",
        "trust",
        "auto_publish_allowed",
        "language",
        "topics",
        "fetch",
        "extract",
        "dedupe",
        "post_rules",
        "enabled",
    ],
    "properties": {
        "id": {
            "type": "string",
            "pattern": "^[a-z0-9][a-z0-9_]*$",
        },
        "track": {"type": "string", "enum": ["A", "B"]},
        "kind": {"type": "string", "enum": ["rss", "github_release"]},
        "endpoint": {"type": "string", "minLength": 1},
        "license_class": {
            "type": "string",
            "enum": ["first_party", "third_party", "mixed"],
        },
        "trust": {"type": "number", "minimum": 0, "maximum": 1},
        "auto_publish_allowed": {"type": "boolean"},
        "respect_robots": {"type": "boolean"},
        "language": {"type": "string", "pattern": "^[a-z]{2}$"},
        "topics": {
            "type": "array",
            "minItems": 1,
            "uniqueItems": True,
            "items": {"type": "string", "minLength": 1},
        },
        "fetch": {
            "type": "object",
            "additionalProperties": False,
            "required": ["interval", "etag", "timeout_sec", "rate_limit"],
            "properties": {
                "interval": {"type": "string", "pattern": "^[0-9]+[hm]$"},
                "etag": {"type": "boolean"},
                "timeout_sec": {"type": "integer", "minimum": 1},
                "rate_limit": {"type": "integer", "minimum": 1},
                "repos": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "string",
                        "pattern": "^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$",
                    },
                },
            },
        },
        "extract": {
            "type": "object",
            "additionalProperties": False,
            "required": ["strategy"],
            "properties": {
                "strategy": {
                    "type": "string",
                    "enum": ["trafilatura", "selectolax"],
                },
            },
        },
        "dedupe": {
            "type": "object",
            "additionalProperties": False,
            "required": ["key", "near_dup"],
            "properties": {
                "key": {"type": "string", "enum": ["canonical_url"]},
                "near_dup": {"type": "string", "enum": ["simhash", "minhash", "none"]},
            },
        },
        "post_rules": {
            "type": "object",
            "additionalProperties": False,
            "required": ["min_words", "require_code_or_figure"],
            "properties": {
                "min_words": {"type": "integer", "minimum": 0},
                "require_code_or_figure": {"type": "boolean"},
            },
        },
        "enabled": {"type": "boolean"},
    },
    "allOf": [
        {
            "if": {"properties": {"kind": {"const": "github_release"}}},
            "then": {"properties": {"fetch": {"required": ["repos"]}}},
        }
    ],
}

VALIDATOR = Draft202012Validator(SOURCE_SCHEMA)


class SourceValidationError(ValueError):
    pass


@dataclass(frozen=True)
class SyncResult:
    source_count: int
    upserted_ids: list[str]
    soft_disabled_ids: list[str]
    dry_run: bool


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def resolve_sources_dir(source_dir: Path | None = None) -> Path:
    if source_dir is not None:
        return source_dir

    from src.config import settings

    return settings.sources_dir


def load_source_file(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        document = yaml.safe_load(handle)

    if not isinstance(document, dict):
        raise SourceValidationError(f"{path.name}: source document must be a mapping")

    validate_source_document(document, source_name=path.name)

    if document["id"] != path.stem:
        raise SourceValidationError(
            f"{path.name}: id must match filename stem '{path.stem}'",
        )

    return document


def validate_source_document(document: dict[str, Any], source_name: str) -> None:
    errors = sorted(VALIDATOR.iter_errors(document), key=lambda error: list(error.path))
    if not errors:
        return

    messages = []
    for error in errors:
        path = ".".join(str(part) for part in error.path) or "<root>"
        messages.append(f"{source_name} [{path}] {error.message}")
    raise SourceValidationError("; ".join(messages))


def load_source_documents(source_dir: Path | None = None) -> list[dict[str, Any]]:
    directory = resolve_sources_dir(source_dir)
    documents = [load_source_file(path) for path in sorted(directory.glob("*.yaml"))]

    if not documents:
        raise SourceValidationError(f"{directory} does not contain any source YAML files")

    return documents


def normalize_source_record(document: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        "id": document["id"],
        "track": document["track"],
        "kind": document["kind"],
        "endpoint": document["endpoint"],
        "license_class": document["license_class"],
        "trust": float(document["trust"]),
        "auto_publish_allowed": bool(document["auto_publish_allowed"]),
        "language": document["language"],
        "topics": document["topics"],
        "fetch_config": {
            **document["fetch"],
            "respect_robots": bool(document.get("respect_robots", True)),
        },
        "extract_config": document["extract"],
        "dedupe_config": document["dedupe"],
        "post_rules": document["post_rules"],
        "enabled": bool(document["enabled"]),
        "config_hash": hash_source_document(document),
        "synced_at": utcnow(),
        "updated_at": utcnow(),
    }
    return normalized


def hash_source_document(document: dict[str, Any]) -> str:
    encoded = json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def sync_sources(
    session: Session,
    source_dir: Path | None = None,
    *,
    dry_run: bool = False,
) -> SyncResult:
    documents = load_source_documents(source_dir)
    records = [normalize_source_record(document) for document in documents]
    yaml_ids = {record["id"] for record in records}
    existing_ids = set(session.scalars(select(Source.id)))
    soft_disabled_ids = sorted(existing_ids - yaml_ids)
    upserted_ids = sorted(yaml_ids)

    if dry_run:
        return SyncResult(
            source_count=len(records),
            upserted_ids=upserted_ids,
            soft_disabled_ids=soft_disabled_ids,
            dry_run=True,
        )

    for record in records:
        stmt = insert(Source).values(**record)
        excluded = stmt.excluded
        update_values = {
            column: getattr(excluded, column)
            for column in record
            if column not in {"id"}
        }
        session.execute(
            stmt.on_conflict_do_update(
                index_elements=[Source.id],
                set_=update_values,
            )
        )

    if soft_disabled_ids:
        now = utcnow()
        session.execute(
            update(Source)
            .where(Source.id.in_(soft_disabled_ids))
            .values(enabled=False, synced_at=now, updated_at=now)
        )

    return SyncResult(
        source_count=len(records),
        upserted_ids=upserted_ids,
        soft_disabled_ids=soft_disabled_ids,
        dry_run=False,
    )


def list_sources(session: Session) -> list[Source]:
    return list(session.scalars(select(Source).order_by(Source.id)))


def serialize_source(source: Source) -> dict[str, Any]:
    return {
        "id": source.id,
        "track": source.track,
        "kind": source.kind,
        "endpoint": source.endpoint,
        "license_class": source.license_class,
        "trust": source.trust,
        "auto_publish_allowed": source.auto_publish_allowed,
        "enabled": source.enabled,
    }


def render_sources_table(sources: list[Source]) -> str:
    headers = ("id", "track", "kind", "enabled", "auto_publish_allowed")
    rows = [
        (
            source.id,
            source.track,
            source.kind,
            "true" if source.enabled else "false",
            "true" if source.auto_publish_allowed else "false",
        )
        for source in sources
    ]
    widths = [
        max(len(header), *(len(row[index]) for row in rows)) if rows else len(header)
        for index, header in enumerate(headers)
    ]

    def format_row(values: tuple[str, ...]) -> str:
        return "  ".join(value.ljust(widths[index]) for index, value in enumerate(values))

    lines = [format_row(headers), format_row(tuple("-" * width for width in widths))]
    lines.extend(format_row(row) for row in rows)
    return "\n".join(lines)
