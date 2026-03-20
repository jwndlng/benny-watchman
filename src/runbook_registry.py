"""Loads and exposes all Runbooks at startup."""

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class Runbook(BaseModel):
    """Runbook parsed from YAML frontmatter + Markdown body."""

    name: str = Field(
        description="Unique runbook identifier — matched against alert type"
    )
    description: str = Field(
        description="Short description of what this runbook covers"
    )
    instructions: str = Field(
        description="Markdown body — becomes the AnalystAgent system prompt"
    )


FRONTMATTER_DELIMITER = "---"


class RunbookRegistry:
    """Loads runbooks from disk and matches them to incoming alert types."""

    def __init__(self) -> None:
        self._runbooks: dict[str, Runbook] = {}

    def load(self, path: str) -> None:
        """Parse all .md runbooks in the given directory and register them by name."""
        for file in Path(path).glob("*.md"):
            runbook = self._parse(file)
            self._runbooks[runbook.name] = runbook

    def get(self, name: str) -> Runbook | None:
        """Return the runbook with the given name, or None if not found."""
        return self._runbooks.get(name)

    def list(self) -> list[Runbook]:
        """Return all loaded runbooks."""
        return list(self._runbooks.values())

    def match(self, alert_type: str) -> Runbook | None:
        """Return the runbook matching the alert type, falling back to 'generic'."""
        return self._runbooks.get(alert_type) or self._runbooks.get("generic")

    def _parse(self, file: Path) -> Runbook:
        """Parse YAML frontmatter and Markdown body from a runbook file."""
        content = file.read_text()
        parts = content.split(FRONTMATTER_DELIMITER, 2)
        frontmatter = yaml.safe_load(parts[1])
        instructions = parts[2].strip() if len(parts) > 2 else ""
        return Runbook(instructions=instructions, **frontmatter)
