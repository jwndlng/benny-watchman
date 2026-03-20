"""Request body for POST /investigate."""

from datetime import datetime

from pydantic import BaseModel, Field


class InvestigateRequest(BaseModel):
    id: str = Field(description="Unique alert identifier")
    type: str = Field(description="Alert type — used to match a runbook")
    title: str = Field(description="Short human-readable alert title")
    description: str = Field(
        description="Full alert description with context for the analyst"
    )
    severity: str = Field(description="Reported severity from the detection source")
    source: str = Field(description="System or tool that generated the alert")
    timestamp: datetime = Field(description="When the alert was triggered")
    raw: dict[str, object] = Field(
        default_factory=dict, description="Raw alert payload from the source system"
    )
