"""Investigation process entity — created when an alert is submitted."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from src.schemas.incident_report import IncidentReport, Severity, Verdict


class InvestigationStatus(str, Enum):
    """Lifecycle state of an investigation."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class Investigation(BaseModel):
    """Investigation process entity — created when an alert is submitted."""

    id: str = Field(description="Unique investigation identifier")
    alert_id: str = Field(
        description="ID of the alert that triggered this investigation"
    )
    status: InvestigationStatus = Field(description="Current investigation status")
    severity: Severity | None = Field(
        default=None, description="Assessed severity, set on completion"
    )
    verdict: Verdict | None = Field(
        default=None, description="Investigation verdict, set on completion"
    )
    runbook: str | None = Field(
        default=None, description="Runbook used for this investigation"
    )
    created_at: datetime = Field(description="When the investigation was created")
    completed_at: datetime | None = Field(
        default=None, description="When the investigation completed"
    )
    report: IncidentReport | None = Field(
        default=None, description="Full incident report, set on completion"
    )
