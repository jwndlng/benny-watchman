"""Investigation process entity — the domain-agnostic persistence envelope.

Created when an alert or finding is submitted. The `report` is an opaque,
serialized domain payload (each module owns its typed report); the `outcome`
is the generic cross-domain summary. This module imports no `src.modules.*`
type, so persistence stays decoupled from any vertical.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from src.schemas.outcome import Outcome


class InvestigationStatus(str, Enum):
    """Lifecycle state of an investigation."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class Investigation(BaseModel):
    """Investigation process entity — domain-agnostic envelope."""

    id: str = Field(description="Unique investigation identifier")
    key: str = Field(
        default="",
        description="Dedup key '<module>:<module dedup key>' — enforces review-once",
    )
    module: str = Field(default="", description="Analyst module that produced this investigation")
    alert_id: str = Field(description="ID of the input (alert or finding) investigated")
    status: InvestigationStatus = Field(description="Current investigation status")
    severity: str | None = Field(default=None, description="Assessed severity, set on completion")
    verdict: str | None = Field(default=None, description="Investigation verdict, set on completion")
    guidance_source: str | None = Field(
        default=None, description="Provenance of the guidance applied (e.g. 'elastic-rule-note'), or None"
    )
    outcome: Outcome | None = Field(default=None, description="Generic cross-domain summary, set on completion")
    created_at: datetime = Field(description="When the investigation was created")
    completed_at: datetime | None = Field(default=None, description="When the investigation completed")
    report: dict[str, object] | None = Field(
        default=None, description="Serialized domain report payload, set on completion"
    )
