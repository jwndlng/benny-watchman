"""VulnTriageReport — the Vulnerability Management triage output."""

from pydantic import BaseModel, Field


class VulnTriageReport(BaseModel):
    finding_id: str = Field(description="ID of the finding triaged")
    exploitable: bool = Field(
        description="Whether the vulnerability is exploitable in this environment"
    )
    priority: str = Field(
        description="Remediation priority (e.g. critical/high/medium/low)"
    )
    remediation_sla_days: int | None = Field(
        default=None, description="Recommended remediation window in days"
    )
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")
    summary: str = Field(description="Concise triage summary")
    affected_assets: list[str] = Field(
        description="Assets affected by this vulnerability"
    )
    evidence: list[str] = Field(description="Key evidence supporting the assessment")
    recommended_actions: list[str] = Field(
        description="Recommended remediation actions"
    )
    investigation_steps: list[str] = Field(description="What was checked, in order")
    investigation_truncated: bool = Field(
        default=False, description="True if the tool call limit was reached"
    )
