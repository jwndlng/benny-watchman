"""Autonomously investigates alerts using a data sufficiency loop.

Bootstrapped by the Orchestrator with a Runbook and a list of pre-initialized
DataAgents. Delegates data retrieval to DataAgents via dynamically registered
query tools, one per source. Iterates until confident in a conclusion or the
tool call limit is reached.
"""

import uuid
from collections.abc import Callable
from datetime import date, datetime, timezone

import logfire
from pydantic import BaseModel, Field
from pydantic_ai import AgentRunResult

from src.agents.base_agent import BaseAgent
from src.agents.data.base_data_agent import BaseDataAgent, DataModel
from src.runbook_registry import Runbook
from src.schemas.alert import Alert
from src.schemas.incident_report import IncidentReport, Severity, Verdict
from src.schemas.investigation import Investigation, InvestigationStatus


def _make_query_tool(data_agent: BaseDataAgent) -> Callable:
    """Create a named async tool function that delegates to the given DataAgent.

    The function name becomes the PydanticAI tool name (query_{agent.name})
    and the docstring becomes the tool description seen by the LLM.
    This factory is the deliberate exception to the no-closures rule — dynamic
    tool names cannot be expressed as fixed methods on AnalystAgent.
    """

    async def query_fn(request: str) -> DataModel:
        with logfire.span(f"query_{data_agent.name}", request=request):
            result: AgentRunResult[DataModel] = await data_agent.run(request)
            return result.output

    query_fn.__name__ = f"query_{data_agent.name}"
    query_fn.__doc__ = data_agent.routing_description
    return query_fn


class UserProfile(BaseModel):
    """Identity and employment context returned by the lookup_user tool."""

    name: str = Field(description="Full name")
    email: str = Field(description="Work email")
    team: str = Field(description="Team or department")
    role: str = Field(description="Job title / role")
    manager: str = Field(description="Direct manager")
    employment_status: str = Field(description="active | on_leave | terminated")
    start_date: date = Field(description="Employment start date")
    termination_date: date | None = Field(
        description="Scheduled termination date if known"
    )
    tenure_days: int = Field(description="Number of days employed as of today")
    work_location: str = Field(description="Primary office location or 'remote'")
    timezone: str = Field(description="Work timezone")
    on_call: bool = Field(description="Currently on call")
    out_of_office: bool = Field(description="Currently OOO")
    access_level: str = Field(description="Expected privilege level for this role")


class AnalystModel(BaseModel):
    severity: Severity = Field(description="Assessed severity of the alert")
    verdict: Verdict = Field(description="Investigation verdict")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")
    summary: str = Field(description="Concise investigation summary")
    affected_entities: list[str] = Field(description="Users, hosts, and IPs involved")
    timeline: list[str] = Field(
        description="Ordered sequence of events found, from earliest to latest"
    )
    investigation_steps: list[str] = Field(
        description="What you checked during the investigation, in order"
    )
    scope: str = Field(
        description="Blast radius — what systems or data could be affected"
    )
    findings: list[str] = Field(description="Key findings and evidence")
    recommended_actions: list[str] = Field(description="Recommended SOC actions")
    detection_rule_improvements: list[str] = Field(
        description="Suggested detection rule improvements"
    )
    investigation_truncated: bool = Field(
        default=False, description="True if the tool call limit was reached"
    )


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
    ) -> None:
        self._runbook = runbook  # must be set before super().__init__ calls self.instructions
        names = [a.name for a in data_agents]
        if len(names) != len(set(names)):
            duplicates = {n for n in names if names.count(n) > 1}
            raise ValueError(f"Duplicate DataAgent names: {duplicates}")
        self._data_agents = data_agents
        super().__init__(
            model=model,
            output_type=AnalystModel,
            name=f"AnalystAgent({runbook.name})",
        )
        for agent in data_agents:
            self.agent.tool_plain(_make_query_tool(agent))
        self.agent.tool_plain(self.lookup_user)

    def lookup_user(self, username: str) -> UserProfile:
        """Look up identity, role, and availability context for a given user.
        Returns employment status, tenure, location, and access level.
        Use this to assess whether activity is expected for this user's role and context."""
        # TODO: wire up to Okta IDP (see change: add-okta-idp)
        return UserProfile(
            name=username,
            email=f"{username}@example.com",
            team="unknown",
            role="unknown",
            manager="unknown",
            employment_status="active",
            start_date=date(2020, 1, 1),
            termination_date=None,
            tenure_days=0,
            work_location="unknown",
            timezone="UTC",
            on_call=False,
            out_of_office=False,
            access_level="unknown",
        )

    def investigate(self, alert: Alert) -> Investigation:
        result = self.run_sync(
            f"Investigate the following alert:\n{alert.model_dump_json()}"
        )
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
            created_at=now,
            completed_at=now,
            report=report,
        )
