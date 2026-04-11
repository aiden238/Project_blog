from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from src.config import settings

PROMPT_FILENAME_PATTERN = re.compile(r"^(?P<task>[a-z_]+)_v(?P<version>\d+)\.txt$")


@dataclass(frozen=True)
class PromptTemplate:
    task: str
    version: int
    body: str

    @property
    def version_id(self) -> str:
        return f"{self.task}_v{self.version}"


def prompts_dir() -> Path:
    return settings.project_root / "src" / "prompts"


def load_prompt_template(task: str, version: int | None = None) -> PromptTemplate:
    directory = prompts_dir()
    matches: list[tuple[int, Path]] = []
    for path in directory.glob(f"{task}_v*.txt"):
        match = PROMPT_FILENAME_PATTERN.match(path.name)
        if not match:
            continue
        matches.append((int(match.group("version")), path))

    if not matches:
        raise FileNotFoundError(f"prompt template not found for task '{task}'")

    if version is None:
        selected_version, selected_path = max(matches, key=lambda item: item[0])
    else:
        selected_version, selected_path = next(
            (
                candidate_version,
                candidate_path,
            )
            for candidate_version, candidate_path in matches
            if candidate_version == version
        )

    return PromptTemplate(
        task=task,
        version=selected_version,
        body=selected_path.read_text(encoding="utf-8").strip(),
    )


def render_prompt(
    task: str,
    context: dict[str, str],
    *,
    version: int | None = None,
) -> PromptTemplate:
    template = load_prompt_template(task, version)
    return PromptTemplate(
        task=template.task,
        version=template.version,
        body=template.body.format(**context),
    )
