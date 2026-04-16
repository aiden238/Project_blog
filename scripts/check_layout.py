#!/usr/bin/env python3
"""
디렉터리 구조·명명 규칙 검증 스크립트.
실패 시 exit 1. CI에서 매 빌드 실행.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

REQUIRED_DIRS = [
    "src", "instructions", "sources", "db/migrations",
    "docker", "scripts", "tests",
    "data/raw", "data/clean", "data/summaries",
    "data/drafts/track_a", "data/drafts/track_b",
    "data/html", "data/backups/restore_drills",
    "data/raw_quarantine", "logs/report", "logs/alembic",
]

FILENAME_PATTERN = re.compile(r'^[a-z0-9][a-z0-9_\-\.]*$')

FORBIDDEN_IN_ROOT = {".env", "secrets.toml"}

errors: list[str] = []


def check_required_dirs() -> None:
    for d in REQUIRED_DIRS:
        path = ROOT / d
        if not path.exists():
            errors.append(f"[MISSING DIR] {d}")


def check_filenames() -> None:
    skip = {".git", ".venv", "__pycache__", "node_modules"}
    for p in ROOT.rglob("*"):
        if any(s in p.parts for s in skip):
            continue
        name = p.name
        # .env.example 처럼 dot으로 시작하는 특수 파일은 허용
        if name.startswith("."):
            continue
        if not FILENAME_PATTERN.match(name.lower()):
            errors.append(f"[BAD FILENAME] {p.relative_to(ROOT)}")


def check_forbidden_files() -> None:
    for name in FORBIDDEN_IN_ROOT:
        if (ROOT / name).exists():
            errors.append(f"[FORBIDDEN IN REPO] {name} — .gitignore 확인")


if __name__ == "__main__":
    check_required_dirs()
    check_filenames()
    check_forbidden_files()

    if errors:
        print("check_layout FAILED:")
        for e in errors:
            print(f"  {e}")
        sys.exit(1)

    print("check_layout OK")
    sys.exit(0)
