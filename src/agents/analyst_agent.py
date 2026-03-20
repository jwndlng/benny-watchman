"""Autonomously investigates alerts using a data sufficiency loop.

Bootstrapped by the Router with a Runbook (system prompt + scoped tool set).
Delegates data retrieval to DataAgent via the query_data tool.
Iterates until confident in a conclusion or the tool call limit is reached.
"""

import uuid
from datetime import date, datetime, timezone

import logfire
from pydantic import BaseModel, Field

from src.agents.base_agent import BaseAgent
from src.agents.data_agent import DataAgent, DataModel
from src.config import config
from src.runbook_registry import Runbook
from src.schemas.alert import Alert
from src.schemas.incident_report import IncidentReport, Severity, Verdict
from src.schemas.investigation import Investigation, InvestigationStatus


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
            "Call query_data at most 2 times total",
            "Issue one query at a time — not multiple in parallel",
            "Stop querying as soon as you have sufficient evidence to reach a verdict",
        ]

    def __init__(
        self, model: str, runbook: Runbook, db_path: str | None = None
    ) -> None:
        self._runbook = (
            runbook  # must be set before super().__init__ calls self.instructions
        )
        self._data_agent: DataAgent = DataAgent.create(
            engine=config.data.engine,
            model=model,
            db_path=db_path or config.data.db_path,
        )
        super().__init__(
            model=model,
            output_type=AnalystModel,
            name=f"AnalystAgent({runbook.name})",
        )
        self.agent.tool_plain(self.query_data)
        self.agent.tool_plain(self.lookup_user)

    async def query_data(self, request: str) -> DataModel:
        """Fetch data from the security log database. Describe what you need in plain English."""
        with logfire.span("query_data", request=request):
            result = await self._data_agent.run(request)
            return result.output

    def lookup_user(self, username: str) -> UserProfile:
        """Look up identity, role, and availability context for a given user.
        Returns employment status, tenure, location, and access level.
        Use this to assess whether activity is expected for this user's role and context."""
        # TODO: wire up to HR / identity provider
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
