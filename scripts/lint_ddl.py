from __future__ import annotations

import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_DIRS = ("src", "scripts", "tests")
SCAN_FILES = ("pipeline.py",)
SKIP_PARTS = {".git", ".venv", "__pycache__", "db", "migrations"}
DDL_PATTERN = re.compile(r"\b(?:CREATE|ALTER|DROP)\s+TABLE\b", re.IGNORECASE)


@dataclass(frozen=True)
class Violation:
    path: Path
    lineno: int
    message: str


def iter_python_files() -> list[Path]:
    files: list[Path] = []

    for directory in SCAN_DIRS:
        root = ROOT / directory
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            if any(part in SKIP_PARTS for part in path.parts):
                continue
            if path.name == "lint_ddl.py":
                continue
            files.append(path)

    for filename in SCAN_FILES:
        path = ROOT / filename
        if path.exists():
            files.append(path)

    return sorted(set(files))


def find_ddl_violations(path: Path) -> list[Violation]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    violations: list[Violation] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        if DDL_PATTERN.search(node.value):
            violations.append(
                Violation(
                    path=path,
                    lineno=node.lineno,
                    message="direct DDL string detected outside Alembic migrations",
                )
            )

    return violations


def main() -> int:
    violations = [violation for path in iter_python_files() for violation in find_ddl_violations(path)]

    if violations:
        print("lint_ddl FAILED:")
        for violation in violations:
            rel_path = violation.path.relative_to(ROOT)
            print(f"  {rel_path}:{violation.lineno} {violation.message}")
        return 1

    print("lint_ddl OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
