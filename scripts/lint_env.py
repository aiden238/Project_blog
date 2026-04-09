from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_DIRS = ("src", "scripts", "tests")
SCAN_FILES = ("pipeline.py",)
SKIP_PARTS = {".git", ".venv", "__pycache__"}


@dataclass(frozen=True)
class Violation:
    path: Path
    lineno: int
    col_offset: int
    message: str


class OsEnvironVisitor(ast.NodeVisitor):
    def __init__(self, path: Path) -> None:
        self.path = path
        self.os_aliases: set[str] = set()
        self.violations: list[Violation] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name == "os":
                self.os_aliases.add(alias.asname or alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module == "os":
            for alias in node.names:
                if alias.name == "environ":
                    self.violations.append(
                        Violation(
                            path=self.path,
                            lineno=node.lineno,
                            col_offset=node.col_offset,
                            message="direct 'from os import environ' is forbidden; use src.config.settings",
                        )
                    )
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if (
            node.attr == "environ"
            and isinstance(node.value, ast.Name)
            and node.value.id in self.os_aliases
        ):
            self.violations.append(
                Violation(
                    path=self.path,
                    lineno=node.lineno,
                    col_offset=node.col_offset,
                    message="direct 'os.environ' access is forbidden; use src.config.settings",
                )
            )
        self.generic_visit(node)


def iter_python_files() -> list[Path]:
    paths: list[Path] = []

    for directory in SCAN_DIRS:
        root = ROOT / directory
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            if any(part in SKIP_PARTS for part in path.parts):
                continue
            paths.append(path)

    for filename in SCAN_FILES:
        path = ROOT / filename
        if path.exists():
            paths.append(path)

    return sorted(set(paths))


def find_violations(path: Path) -> list[Violation]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    visitor = OsEnvironVisitor(path)
    visitor.visit(tree)
    return visitor.violations


def main() -> int:
    violations = [violation for path in iter_python_files() for violation in find_violations(path)]

    if violations:
        print("lint_env FAILED:")
        for violation in violations:
            rel_path = violation.path.relative_to(ROOT)
            print(
                f"  {rel_path}:{violation.lineno}:{violation.col_offset} {violation.message}"
            )
        return 1

    print("lint_env OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
