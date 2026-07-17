"""Autonomously triages vulnerability findings using a data sufficiency loop.

Bootstrapped by the VM module with pre-initialized DataAgents (asset inventory)
and a vuln-intel tool. Iterates until confident in a triage verdict or the tool
call limit is reached.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import logfire
from pydantic import BaseModel, Field

from src.capabilities.data.base_data_agent import BaseDataAgent
from src.capabilities.data.query_tool import make_query_tool
from src.core.agents.base_agent import BaseAgent
from src.modules.vuln_mgmt.finding import Finding
from src.modules.vuln_mgmt.intel import VulnIntelCapability
from src.modules.vuln_mgmt.report import VulnTriageReport
from src.schemas.guidance import TRUST_SEAM, format_guidance
from src.schemas.investigation import Investigation, InvestigationStatus
from src.schemas.outcome import Outcome


_VULN_METHOD = """You are Benny, an autonomous vulnerability-management analyst triaging a finding.

Work the finding the way a real analyst does:
1. Review the finding — CVE, affected asset, and CVSS base score.
2. Read the description and any attached investigation guidance.
3. Enrich the CVE with threat intelligence (EPSS, KEV) to gauge real-world exploitability.
4. Query the asset inventory to establish exposure — internet-facing? what does it run? who owns it?
5. Decide whether the vulnerability is exploitable in this environment, and assign a
   remediation priority and SLA with supporting evidence.

Be conservative — if exposure is unclear, prefer a higher priority and flag for manual review."""


class VulnAnalystModel(BaseModel):
    exploitable: bool = Field(
        description="Whether the vulnerability is exploitable in this environment"
    )
    priority: str = Field(description="Remediation priority (critical/high/medium/low)")
    remediation_sla_days: int | None = Field(
        default=None, description="Recommended remediation window in days"
    )
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")
    summary: str = Field(description="Concise triage summary")
    affected_assets: list[str] = Field(description="Assets affected")
    evidence: list[str] = Field(description="Key evidence supporting the assessment")
    recommended_actions: list[str] = Field(
        description="Recommended remediation actions"
    )
    investigation_steps: list[str] = Field(description="What you checked, in order")
    investigation_truncated: bool = Field(
        default=False, description="True if the tool call limit was reached"
    )


class VulnAnalystAgent(BaseAgent[VulnAnalystModel]):
    @property
    def instructions(self) -> str:
        return f"{_VULN_METHOD}\n\n{TRUST_SEAM}"

    @property
    def constraints(self) -> list[str]:
        return [
            "Call each data source tool at most 2 times",
            "Enrich the CVE once before reaching a verdict",
            "Stop querying as soon as you have sufficient evidence",
        ]

    def __init__(
        self,
        model: str,
        data_agents: list[BaseDataAgent],
        intel: VulnIntelCapability,
    ) -> None:
        names = [a.name for a in data_agents]
        if len(names) != len(set(names)):
            duplicates = {n for n in names if names.count(n) > 1}
            raise ValueError(f"Duplicate DataAgent names: {duplicates}")
        self._data_agents = data_agents
        self._intel = intel
        super().__init__(
            model=model,
            output_type=VulnAnalystModel,
            name="VulnAnalystAgent(vuln_mgmt)",
        )
        for agent in data_agents:
            self.agent.tool_plain(make_query_tool(agent))
        self.agent.tool_plain(self.enrich_cve)

    async def enrich_cve(self, cve: str) -> dict[str, object]:
        """Enrich a CVE with threat intelligence (EPSS score, KEV membership, references).
        Input: a CVE identifier like 'CVE-2024-1234'.
        Use this to gauge real-world exploitability before reaching a verdict."""
        return await self._intel.enrich(cve)

    def investigate(self, finding: Finding) -> Investigation:
        guidance = finding.guidance
        logfire.info(
            "triage guidance",
            item_id=finding.id,
            module="vuln_mgmt",
            present=guidance is not None,
            source=guidance.source if guidance else None,
            length=len(guidance.text) if guidance else 0,
        )
        result = self.run_sync(
            f"Triage the following vulnerability finding:\n"
            f"{finding.model_dump_json(exclude={'guidance'})}"
            f"{format_guidance(guidance)}"
        )
        m = result.output
        report = VulnTriageReport(
            finding_id=finding.id,
            exploitable=m.exploitable,
            priority=m.priority,
            remediation_sla_days=m.remediation_sla_days,
            confidence=m.confidence,
            summary=m.summary,
            affected_assets=m.affected_assets,
            evidence=m.evidence,
            recommended_actions=m.recommended_actions,
            investigation_steps=m.investigation_steps,
            investigation_truncated=m.investigation_truncated,
        )
        now = datetime.now(timezone.utc)
        return Investigation(
            id=str(uuid.uuid4()),
            alert_id=finding.id,
            status=InvestigationStatus.COMPLETE,
            guidance_source=guidance.source if guidance else None,
            outcome=Outcome(
                disposition="exploitable" if m.exploitable else "not_exploitable",
                priority=m.priority,
            ),
            created_at=now,
            completed_at=now,
            report=report.model_dump(mode="json"),
        )
