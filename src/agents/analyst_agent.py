"""Autonomously investigates alerts using a data sufficiency loop.

Bootstrapped by the Router with a Runbook (system prompt + scoped tool set).
Delegates data retrieval to DataAgent via the query_data tool.
Iterates until confident in a conclusion or the tool call limit is reached.
"""

import uuid
from datetime import datetime, timezone

import logfire
from pydantic import BaseModel, Field

from src.agents.base_agent import BaseAgent
from src.agents.data_agent import DataAgent, DataModel
from src.config import config
from src.schemas.runbook import Runbook
from src.schemas.alert import Alert
from src.schemas.incident_report import IncidentReport, Severity, Verdict
from src.schemas.investigation import Investigation, InvestigationStatus


class AnalystModel(BaseModel):
    severity: Severity = Field(description="Assessed severity of the alert")
    verdict: Verdict = Field(description="Investigation verdict")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")
    summary: str = Field(description="Concise investigation summary")
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

    _data_agent: DataAgent

    def __init__(
        self, model: str, runbook: Runbook, db_path: str | None = None
    ) -> None:
        self._runbook = (
            runbook  # must be set before super().__init__ calls self.instructions
        )
        self._data_agent = DataAgent.create(
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

    async def query_data(self, request: str) -> DataModel:
        """Fetch data from the security log database. Describe what you need in plain English."""
        with logfire.span("query_data", request=request):
            result = await self._data_agent.run(request)
            return result.output

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
