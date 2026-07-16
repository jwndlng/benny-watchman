"""Finding — the Vulnerability Management input contract."""

from datetime import datetime

from pydantic import BaseModel, Field


class Finding(BaseModel):
    id: str = Field(description="Unique finding identifier")
    type: str = Field(description="Vulnerability class — used to match a runbook")
    cve: str = Field(description="CVE identifier, e.g. CVE-2024-1234")
    asset: str = Field(description="Affected asset identifier (host, IP, or asset id)")
    cvss: float = Field(description="CVSS base score, 0.0–10.0")
    title: str = Field(description="Short human-readable finding title")
    description: str = Field(description="Full finding description with context for triage")
    source: str = Field(description="Scanner or tool that produced the finding")
    detected_at: datetime = Field(description="When the finding was detected")
    raw: dict[str, object] = Field(default_factory=dict, description="Raw finding payload from the scanner")
