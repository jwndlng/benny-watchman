"""Autonomously triages vulnerability findings using a data sufficiency loop.

Bootstrapped by the VM module with a Runbook, pre-initialized DataAgents (asset
inventory), and a vuln-intel tool. Iterates until confident in a triage verdict
or the tool call limit is reached.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from src.capabilities.subagents.data.base_data_agent import BaseDataAgent
from src.capabilities.subagents.data.query_tool import make_query_tool
from src.core.agents.base_agent import BaseAgent
from src.core.orchestration.runbook_registry import Runbook
from src.modules.vuln_mgmt.schemas.finding import Finding
from src.modules.vuln_mgmt.tools.intel import VulnIntelCapability
from src.modules.vuln_mgmt.schemas.report import VulnTriageReport
from src.schemas.investigation import Investigation, InvestigationStatus
from src.schemas.outcome import Outcome


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
        return self._runbook.instructions

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
        runbook: Runbook,
        data_agents: list[BaseDataAgent],
        intel: VulnIntelCapability,
    ) -> None:
        self._runbook = runbook
        names = [a.name for a in data_agents]
        if len(names) != len(set(names)):
            duplicates = {n for n in names if names.count(n) > 1}
            raise ValueError(f"Duplicate DataAgent names: {duplicates}")
        self._data_agents = data_agents
        self._intel = intel
        super().__init__(
            model=model,
            output_type=VulnAnalystModel,
            name=f"VulnAnalystAgent({runbook.name})",
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
        result = self.run_sync(
            f"Triage the following vulnerability finding:\n{finding.model_dump_json()}"
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
            runbook=self._runbook.name,
            outcome=Outcome(
                disposition="exploitable" if m.exploitable else "not_exploitable",
                priority=m.priority,
            ),
            created_at=now,
            completed_at=now,
            report=report.model_dump(mode="json"),
        )
