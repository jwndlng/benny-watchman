"""Runbook data model parsed from YAML frontmatter + Markdown."""

from pydantic import BaseModel


class Runbook(BaseModel):
    name: str
    description: str
    instructions: str  # markdown body — becomes the AnalystAgent system prompt
