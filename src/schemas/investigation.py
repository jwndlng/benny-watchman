"""Investigation process entity — created when an alert is submitted."""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel
from src.schemas.incident_report import IncidentReport, Severity, Verdict


class InvestigationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class Investigation(BaseModel):
    id: str
    alert_id: str
    status: InvestigationStatus
    severity: Severity | None = None
    verdict: Verdict | None = None
    runbook: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
    report: IncidentReport | None = None
