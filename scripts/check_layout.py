#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_DIRS = [
    "src",
    "instructions",
    "sources",
    "db/migrations",
    "docker",
    "scripts",
    "tests",
    "data/raw",
    "data/clean",
    "data/summaries",
    "data/drafts/track_a",
    "data/drafts/track_b",
    "data/html",
    "data/backups/restore_drills",
    "data/raw_quarantine",
    "docs",
    "logs/alembic",
    "logs/report",
]
EXPECTED_TOP_LEVEL_DIRS = {
    ".git",
    "data",
    "db",
    "docker",
    "docs",
    "instructions",
    "logs",
    "scripts",
    "sources",
    "src",
    "tests",
    ".venv",
    "__pycache__",
}
GENERAL_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9._-]*$")
RAW_FILENAME_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}Z_[a-z0-9_]+_[a-f0-9]{12}\.[a-z0-9]+$"
)
FORBIDDEN_IN_ROOT = {"secrets.toml"}

errors: list[str] = []


def check_required_dirs() -> None:
    for directory in REQUIRED_DIRS:
        path = ROOT / directory
        if not path.exists():
            errors.append(f"[MISSING DIR] {directory}")


def check_top_level_dirs() -> None:
    for path in ROOT.iterdir():
        if not path.is_dir():
            continue
        if path.name not in EXPECTED_TOP_LEVEL_DIRS:
            errors.append(f"[UNDOCUMENTED TOP-LEVEL DIR] {path.name}")


def check_general_names() -> None:
    skip = {".git", ".venv", "__pycache__"}
    for path in ROOT.rglob("*"):
        if any(part in skip for part in path.parts):
            continue
        if path.name.startswith("."):
            continue
        if not GENERAL_NAME_PATTERN.match(path.name):
            errors.append(f"[BAD NAME] {path.relative_to(ROOT)}")


def check_raw_filenames() -> None:
    raw_root = ROOT / "data" / "raw"
    if not raw_root.exists():
        return

    for path in raw_root.rglob("*"):
        if path.is_dir():
            if not re.fullmatch(r"[a-z0-9_]+", path.name):
                errors.append(f"[BAD SOURCE DIR] {path.relative_to(ROOT)}")
            continue
        if not RAW_FILENAME_PATTERN.match(path.name):
            errors.append(f"[BAD RAW FILENAME] {path.relative_to(ROOT)}")


def check_forbidden_files() -> None:
    for name in FORBIDDEN_IN_ROOT:
        if (ROOT / name).exists():
            errors.append(f"[FORBIDDEN IN REPO] {name}")


def main() -> int:
    check_required_dirs()
    check_top_level_dirs()
    check_general_names()
    check_raw_filenames()
    check_forbidden_files()

    if errors:
        print("check_layout FAILED:")
        for error in errors:
            print(f"  {error}")
        return 1

    print("check_layout OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
