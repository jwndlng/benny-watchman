"""Incident Report returned to the caller after investigation."""

from enum import Enum
from pydantic import BaseModel


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
    alert_id: str
    severity: Severity
    verdict: Verdict
    confidence: float
    summary: str
    findings: list[str]
    recommended_actions: list[str]
    detection_rule_improvements: list[str]
    runbook: str
    investigation_truncated: bool = False
