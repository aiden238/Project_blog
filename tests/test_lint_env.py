from __future__ import annotations

from pathlib import Path

from scripts.lint_env import find_violations


def test_lint_env_detects_os_environ_usage(tmp_path: Path) -> None:
    path = tmp_path / "bad.py"
    path.write_text(
        "import os\nvalue = os.environ['DATABASE_URL']\n",
        encoding="utf-8",
    )

    violations = find_violations(path)

    assert violations
    assert "os.environ" in violations[0].message
