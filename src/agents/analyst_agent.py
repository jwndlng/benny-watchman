"""Autonomously investigates alerts using a data sufficiency loop.

Bootstrapped by the Router with a Runbook (system prompt + scoped tool set).
Delegates data retrieval to DataAgent via the query_data tool.
Iterates until confident in a conclusion or the tool call limit is reached.
"""

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from src.agents.base import BaseAgent
from src.agents.data_agent import DataModel
from src.agents.data_sqlite_agent import DataSQLiteAgent
from src.runbook.model import Runbook
from src.schemas.alert import Alert
from src.schemas.incident_report import IncidentReport, Severity, Verdict
from src.schemas.investigation import Investigation, InvestigationStatus

_DATA_AGENT_INSTRUCTIONS = (
    "You are a database expert. Use list_tables to discover available tables, "
    "get_schema to understand their structure, get_sample to preview data, "
    "and run_query to execute SQL queries. Always check schema before writing queries."
)


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
    def __init__(self, model: str, runbook: Runbook, db_path: str) -> None:
        super().__init__(
            model=model,
            output_type=AnalystModel,
            instructions=runbook.instructions,
        )
        self._runbook = runbook

        # TODO: hardcoded to SQLite — replace with dynamic backend selection
        #       once multi-backend support is introduced (see pm/AGENT_DESIGN.md).
        data_agent = DataSQLiteAgent(
            model=model, instructions=_DATA_AGENT_INSTRUCTIONS, db_path=db_path
        )

        @self.agent.tool_plain
        async def query_data(request: str) -> DataModel:
            result = await data_agent.agent.run(request)
            return result.output

    def investigate(self, alert: Alert) -> Investigation:
        result = self.agent.run_sync(
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
