from __future__ import annotations

import argparse
import json
import sys

from sqlalchemy.exc import SQLAlchemyError

from src.db import session_scope
from src.source_registry import (
    SourceValidationError,
    list_sources,
    render_sources_table,
    serialize_source,
    sync_sources,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    sources_parser = subparsers.add_parser("sources", help="Manage source registry entries")
    sources_subparsers = sources_parser.add_subparsers(dest="sources_command", required=True)

    sync_parser = sources_subparsers.add_parser("sync", help="Sync YAML sources into Postgres")
    sync_parser.add_argument("--dry-run", action="store_true", help="Print changes without writing")

    list_parser = sources_subparsers.add_parser("list", help="List sources from Postgres")
    list_parser.add_argument(
        "--format",
        choices=("table", "json"),
        default="table",
        help="Output format",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "sources":
            return handle_sources(args)
    except SourceValidationError as error:
        print(f"source validation failed: {error}", file=sys.stderr)
        return 1
    except SQLAlchemyError as error:
        print(f"database operation failed: {error}", file=sys.stderr)
        return 1

    parser.print_help()
    return 1


def handle_sources(args: argparse.Namespace) -> int:
    if args.sources_command == "sync":
        with session_scope() as session:
            result = sync_sources(session, dry_run=args.dry_run)
        mode = "dry-run" if result.dry_run else "applied"
        print(f"sync {mode}: {result.source_count} source(s)")
        print("upserted:", ", ".join(result.upserted_ids))
        if result.soft_disabled_ids:
            print("soft-disabled:", ", ".join(result.soft_disabled_ids))
        else:
            print("soft-disabled: none")
        return 0

    if args.sources_command == "list":
        with session_scope() as session:
            sources = list_sources(session)

        if args.format == "json":
            payload = [serialize_source(source) for source in sources]
            print(json.dumps(payload, indent=2))
        else:
            print(render_sources_table(sources))
        return 0

    return 1
