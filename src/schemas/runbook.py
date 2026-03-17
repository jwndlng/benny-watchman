"""Runbook data model parsed from YAML frontmatter + Markdown."""

from pydantic import BaseModel, Field


class Runbook(BaseModel):
    name: str = Field(
        description="Unique runbook identifier — matched against alert type"
    )
    description: str = Field(
        description="Short description of what this runbook covers"
    )
    instructions: str = Field(
        description="Markdown body — becomes the AnalystAgent system prompt"
    )
