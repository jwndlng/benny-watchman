"""Critically re-examines AnalystAgent findings and produces the Incident Report.

Applies a skeptical lens — does the evidence support the verdict?
Does not call tools; reasons over provided findings only.

Post-MVP.
"""

from pydantic import BaseModel, Field

from src.agents.base import BaseAgent
from src.schemas.incident_report import IncidentReport


class ReviewerModel(BaseModel):
    findings: list[str] = Field(description="Findings from the AnalystAgent to review")
    draft_report: IncidentReport = Field(description="Draft report to critically examine")


class ReviewerAgent(BaseAgent[ReviewerModel, IncidentReport]):

    def __init__(self, model: str, instructions: str) -> None:
        super().__init__(model=model, output_type=IncidentReport, instructions=instructions)
