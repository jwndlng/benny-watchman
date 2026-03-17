"""Critically re-examines AnalystAgent findings and produces the Incident Report.

Applies a skeptical lens — does the evidence support the verdict?
Does not call tools; reasons over provided findings only.

Post-MVP.
"""

from src.agents.base_agent import BaseAgent
from src.schemas.incident_report import IncidentReport


class ReviewerAgent(BaseAgent[IncidentReport]):
    @property
    def instructions(self) -> str:
        return (
            "You are a skeptical security reviewer. Critically re-examine the provided findings "
            "and assess whether the evidence supports the verdict. Reason only over what is given — "
            "do not call tools."
        )

    def __init__(self, model: str) -> None:
        super().__init__(model=model, output_type=IncidentReport, name="ReviewerAgent")
