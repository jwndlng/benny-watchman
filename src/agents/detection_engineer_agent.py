"""Drafts optimized detection rules based on completed Incident Reports.

Triggered for false positive verdicts or where rule improvements are suggested.
Outputs a draft rule change with explanation.

Post-MVP.
"""

from pydantic import BaseModel, Field

from src.agents.base import BaseAgent
from src.schemas.incident_report import IncidentReport


class DetectionEngineerModel(BaseModel):
    report: IncidentReport = Field(
        description="The incident report to base the rule improvement on"
    )


class DetectionEngineerResult(BaseModel):
    rule: str = Field(description="The drafted detection rule")
    explanation: str = Field(description="Explanation of the changes made")


class DetectionEngineerAgent(
    BaseAgent[DetectionEngineerModel, DetectionEngineerResult]
):
    def __init__(self, model: str, instructions: str) -> None:
        super().__init__(
            model=model,
            output_type=DetectionEngineerResult,
            instructions=instructions,
        )
