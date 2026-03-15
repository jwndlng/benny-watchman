"""Critically re-examines AnalystAgent findings and produces the Incident Report.

Applies a skeptical lens — does the evidence support the verdict?
Does not call tools; reasons over provided findings only.

Post-MVP.
"""

from src.agents.base import BaseAgent
from src.schemas.incident_report import IncidentReport


class ReviewerAgent(BaseAgent[IncidentReport]):
    def __init__(self, model: str, instructions: str) -> None:
        super().__init__(
            model=model, output_type=IncidentReport, instructions=instructions
        )
