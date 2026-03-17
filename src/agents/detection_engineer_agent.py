"""Drafts optimized detection rules based on completed Incident Reports.

Triggered for false positive verdicts or where rule improvements are suggested.
Outputs a draft rule change with explanation.

Post-MVP.
"""

from pydantic import BaseModel, Field

from src.agents.base_agent import BaseAgent


class DetectionEngineerModel(BaseModel):
    rule: str = Field(description="The drafted detection rule")
    explanation: str = Field(description="Explanation of the changes made")


class DetectionEngineerAgent(BaseAgent[DetectionEngineerModel]):
    @property
    def instructions(self) -> str:
        return (
            "You are a detection engineering expert. Based on the provided incident report, "
            "draft an optimized detection rule with a clear explanation of the changes."
        )

    def __init__(self, model: str) -> None:
        super().__init__(
            model=model,
            output_type=DetectionEngineerModel,
            name="DetectionEngineerAgent",
        )
