"""Loads and exposes all Runbooks at startup."""

import yaml
from pathlib import Path

from src.schemas.runbook import Runbook

FRONTMATTER_DELIMITER = "---"


class RunbookRegistry:
    def __init__(self) -> None:
        self._runbooks: dict[str, Runbook] = {}

    def load(self, path: str) -> None:
        for file in Path(path).glob("*.md"):
            runbook = self._parse(file)
            self._runbooks[runbook.name] = runbook

    def get(self, name: str) -> Runbook | None:
        return self._runbooks.get(name)

    def list(self) -> list[Runbook]:
        return list(self._runbooks.values())

    def match(self, alert_type: str) -> Runbook | None:
        return self._runbooks.get(alert_type) or self._runbooks.get("generic")

    def _parse(self, file: Path) -> Runbook:
        content = file.read_text()
        parts = content.split(FRONTMATTER_DELIMITER, 2)
        frontmatter = yaml.safe_load(parts[1])
        instructions = parts[2].strip() if len(parts) > 2 else ""
        return Runbook(instructions=instructions, **frontmatter)
