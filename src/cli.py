from __future__ import annotations

import argparse
import json
import sys

from sqlalchemy.exc import SQLAlchemyError

from src.collection import CollectionService, render_collection_result
from src.db import session_scope
from src.drafting import DraftService
from src.reporting import build_fetch_health_report
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

    fetch_parser = subparsers.add_parser(
        "fetch",
        help="Collect source content into LocalFS and Postgres",
    )
    fetch_parser.add_argument("--source", help="Fetch a single source id")
    fetch_parser.add_argument("--limit", type=int, help="Maximum number of candidates per source")
    fetch_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without writing files or items",
    )
    fetch_parser.add_argument(
        "--format",
        choices=("json", "text"),
        default="text",
        help="Output format",
    )

    draft_parser = subparsers.add_parser("draft", help="Generate drafts from clean items")
    draft_parser.add_argument("--source", help="Generate drafts for a single source id")
    draft_parser.add_argument("--limit", type=int, help="Maximum items to draft")
    draft_parser.add_argument("--dry-run", action="store_true", help="Run without writing drafts")
    draft_parser.add_argument(
        "--format",
        choices=("json", "text"),
        default="text",
        help="Output format",
    )

    report_parser = subparsers.add_parser("report", help="Generate operational reports")
    report_subparsers = report_parser.add_subparsers(dest="report_command", required=True)
    report_subparsers.add_parser("fetch-health", help="Show 7-day fetch failure summary")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "sources":
            return handle_sources(args)
        if args.command == "fetch":
            return handle_fetch(args)
        if args.command == "draft":
            return handle_draft(args)
        if args.command == "report":
            return handle_report(args)
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


def handle_fetch(args: argparse.Namespace) -> int:
    with session_scope(commit=not args.dry_run) as session:
        service = CollectionService(session)
        result = service.fetch_sources(
            source_id=args.source,
            limit=args.limit,
            dry_run=args.dry_run,
        )

    if args.format == "json":
        print(render_collection_result(result))
    else:
        print(f"sources_processed: {result.sources_processed}")
        print(f"candidates_seen: {result.candidates_seen}")
        print(f"items_written: {result.items_written}")
        print(f"duplicates_skipped: {result.duplicates_skipped}")
        print(f"extract_failed: {result.extract_failed}")
        print(f"suspicious_items: {result.suspicious_items}")
        print(f"not_modified: {result.not_modified}")
        print(f"rate_limited: {result.rate_limited}")
        print(f"robots_blocked: {result.robots_blocked}")
    return 0


def handle_report(args: argparse.Namespace) -> int:
    if args.report_command == "fetch-health":
        with session_scope(commit=False) as session:
            print(build_fetch_health_report(session))
        return 0

    return 1


def handle_draft(args: argparse.Namespace) -> int:
    with session_scope(commit=not args.dry_run) as session:
        service = DraftService(session)
        result = service.generate_drafts(
            source_id=args.source,
            limit=args.limit,
            dry_run=args.dry_run,
        )

    payload = {
        "items_seen": result.items_seen,
        "drafts_written": result.drafts_written,
        "llm_failed": result.llm_failed,
        "outbox_enqueued": result.outbox_enqueued,
    }
    if args.format == "json":
        print(json.dumps(payload, indent=2))
    else:
        for key, value in payload.items():
            print(f"{key}: {value}")
    return 0
