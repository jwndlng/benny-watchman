"""Autonomously investigates alerts using a data sufficiency loop.

Bootstrapped by the SIEM module with a Runbook and pre-initialized DataAgents.
Delegates data retrieval to DataAgents via dynamically registered query tools,
one per source. Iterates until confident in a conclusion or the tool call limit
is reached.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from src.capabilities.subagents.data.base_data_agent import BaseDataAgent
from src.capabilities.subagents.data.query_tool import make_query_tool
from src.capabilities.tools.identity.user_profile import UserProfile
from src.core.agents.base_agent import BaseAgent
from src.core.orchestration.runbook_registry import Runbook
from src.modules.siem.schemas.alert import Alert
from src.modules.siem.schemas.incident_report import IncidentReport, Severity, Verdict
from src.schemas.investigation import Investigation, InvestigationStatus
from src.schemas.outcome import Outcome

if TYPE_CHECKING:
    from src.capabilities.tools.identity.assessment import IdentityTool


class AnalystModel(BaseModel):
    severity: Severity = Field(description="Assessed severity of the alert")
    verdict: Verdict = Field(description="Investigation verdict")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")
    summary: str = Field(description="Concise investigation summary")
    affected_entities: list[str] = Field(description="Users, hosts, and IPs involved")
    timeline: list[str] = Field(description="Ordered sequence of events found, from earliest to latest")
    investigation_steps: list[str] = Field(description="What you checked during the investigation, in order")
    scope: str = Field(description="Blast radius — what systems or data could be affected")
    findings: list[str] = Field(description="Key findings and evidence")
    recommended_actions: list[str] = Field(description="Recommended SOC actions")
    detection_rule_improvements: list[str] = Field(description="Suggested detection rule improvements")
    investigation_truncated: bool = Field(default=False, description="True if the tool call limit was reached")


class AnalystAgent(BaseAgent[AnalystModel]):
    @property
    def instructions(self) -> str:
        return self._runbook.instructions

    @property
    def constraints(self) -> list[str]:
        return [
            "Call each data source tool at most 2 times",
            "Issue one query at a time — not multiple in parallel",
            "Stop querying as soon as you have sufficient evidence to reach a verdict",
        ]

    def __init__(
        self,
        model: str,
        runbook: Runbook,
        data_agents: list[BaseDataAgent],
        identity: IdentityTool | None = None,
    ) -> None:
        self._runbook = runbook  # must be set before super().__init__ calls self.instructions
        names = [a.name for a in data_agents]
        if len(names) != len(set(names)):
            duplicates = {n for n in names if names.count(n) > 1}
            raise ValueError(f"Duplicate DataAgent names: {duplicates}")
        self._data_agents = data_agents
        self._identity = identity
        super().__init__(
            model=model,
            output_type=AnalystModel,
            name=f"AnalystAgent({runbook.name})",
        )
        for agent in data_agents:
            self.agent.tool_plain(make_query_tool(agent))
        self.agent.tool_plain(self.lookup_user)

    async def lookup_user(self, username: str) -> UserProfile | None:
        """Look up identity, role, and availability context for a given user.
        Returns employment status, tenure, location, and access level.
        Use this to assess whether activity is expected for this user's role and context.
        Returns None if identity context is unavailable."""
        if self._identity is not None:
            return await self._identity.lookup_user(username)
        return None

    def investigate(self, alert: Alert) -> Investigation:
        result = self.run_sync(f"Investigate the following alert:\n{alert.model_dump_json()}")
        m = result.output
        report = IncidentReport(
            alert_id=alert.id,
            severity=m.severity,
            verdict=m.verdict,
            confidence=m.confidence,
            summary=m.summary,
            affected_entities=m.affected_entities,
            timeline=m.timeline,
            investigation_steps=m.investigation_steps,
            scope=m.scope,
            findings=m.findings,
            recommended_actions=m.recommended_actions,
            detection_rule_improvements=m.detection_rule_improvements,
            runbook=self._runbook.name,
            investigation_truncated=m.investigation_truncated,
        )
        now = datetime.now(timezone.utc)
        return Investigation(
            id=str(uuid.uuid4()),
            alert_id=alert.id,
            status=InvestigationStatus.COMPLETE,
            severity=report.severity,
            verdict=report.verdict,
            runbook=self._runbook.name,
            outcome=Outcome(disposition=m.verdict, priority=m.severity),
            created_at=now,
            completed_at=now,
            report=report.model_dump(mode="json"),
        )
