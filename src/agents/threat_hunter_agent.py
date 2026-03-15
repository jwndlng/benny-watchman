"""Runs interactive, ad-hoc threat hunts against log data.

Accepts a hypothesis or hunt goal from an analyst and autonomously executes
queries via the DataAgent to find supporting or refuting evidence.
Returns a structured hunt report with findings and raw evidence.

Post-MVP.
"""

from pydantic import BaseModel, Field

from src.agents.base import BaseAgent


class ThreatHunterModel(BaseModel):
    hypothesis: str = Field(
        description="The threat hypothesis or hunt goal to investigate"
    )
    scope: str = Field(description="Time range, systems, or data sources to focus on")


class ThreatHunterResult(BaseModel):
    hypothesis: str = Field(description="The original hypothesis")
    verdict: str = Field(description="supported | refuted | inconclusive")
    findings: list[str] = Field(description="Evidence found during the hunt")
    queries_run: list[str] = Field(
        description="Queries executed against the data backend"
    )
    recommended_actions: list[str] = Field(
        description="Suggested next steps for the analyst"
    )


class ThreatHunterAgent(BaseAgent[ThreatHunterModel, ThreatHunterResult]):
    def __init__(self, model: str, instructions: str) -> None:
        super().__init__(
            model=model,
            output_type=ThreatHunterResult,
            instructions=instructions,
        )
