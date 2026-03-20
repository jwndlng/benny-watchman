"""Incident Report returned to the caller after investigation."""

from enum import Enum
from pydantic import BaseModel, Field


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class Verdict(str, Enum):
    TRUE_POSITIVE = "true_positive"
    FALSE_POSITIVE = "false_positive"
    INCONCLUSIVE = "inconclusive"


class IncidentReport(BaseModel):
    alert_id: str = Field(
        description="ID of the alert that triggered this investigation"
    )
    severity: Severity = Field(description="Assessed severity")
    verdict: Verdict = Field(description="Investigation verdict")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")
    summary: str = Field(description="Concise investigation summary")
    affected_entities: list[str] = Field(description="Users, hosts, and IPs involved")
    timeline: list[str] = Field(
        description="Ordered sequence of events found during investigation"
    )
    investigation_steps: list[str] = Field(
        description="What the agent checked, in order"
    )
    scope: str = Field(
        description="Blast radius — what systems or data could be affected"
    )
    findings: list[str] = Field(description="Key findings and evidence")
    recommended_actions: list[str] = Field(description="Recommended SOC actions")
    detection_rule_improvements: list[str] = Field(
        description="Suggested detection rule improvements"
    )
    runbook: str = Field(description="Runbook used for this investigation")
    investigation_truncated: bool = Field(
        default=False, description="True if the tool call limit was reached"
    )
