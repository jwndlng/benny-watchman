"""Incoming alert structure from the REST API."""

from datetime import datetime

from pydantic import BaseModel, Field

from src.modules.siem.schemas.incident_report import Severity
from src.schemas.guidance import InvestigationGuidance


class Alert(BaseModel):
    id: str = Field(description="Unique alert identifier")
    type: str = Field(description="Alert type — metadata and dedup key")
    title: str = Field(description="Short human-readable alert title")
    description: str = Field(description="Full alert description with context for the analyst")
    severity: Severity = Field(description="Reported severity from the detection source")
    source: str = Field(description="System or tool that generated the alert")
    timestamp: datetime = Field(description="When the alert was triggered")
    raw: dict[str, object] = Field(default_factory=dict, description="Raw alert payload from the source system")
    guidance: InvestigationGuidance | None = Field(
        default=None, description="Investigation guidance attached to the alert (a lead, not a command)"
    )
