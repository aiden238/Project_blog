from __future__ import annotations

from pathlib import Path

from scripts.lint_ddl import find_ddl_violations


def test_lint_ddl_detects_direct_table_ddl(tmp_path: Path) -> None:
    path = tmp_path / "bad_sql.py"
    ddl = "CREATE" + " TABLE items (id int)"
    path.write_text(
        f'SQL = "{ddl}"\n',
        encoding="utf-8",
    )

    violations = find_ddl_violations(path)

    assert violations
    assert "DDL" in violations[0].message
