"""Autonomously investigates alerts using a data sufficiency loop.

Bootstrapped by the Router with a Runbook (system prompt + scoped tool set).
Delegates data retrieval to DataAgent and enrichment to EnrichmentAgent.
Iterates until confident in a conclusion or the tool call limit is reached.
"""

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from src.agents.base import BaseAgent
from src.runbook.model import Runbook
from src.schemas.alert import Alert
from src.schemas.incident_report import IncidentReport
from src.schemas.investigation import Investigation, InvestigationStatus


class AnalystModel(BaseModel):
    alert: Alert = Field(description="The alert being investigated")
    runbook: Runbook = Field(description="The runbook guiding this investigation")


class AnalystAgent(BaseAgent[AnalystModel, IncidentReport]):
    def __init__(self, model: str, runbook: Runbook) -> None:
        super().__init__(
            model=model,
            output_type=IncidentReport,
            instructions=runbook.instructions,
        )
        self._runbook = runbook

    def investigate(self, alert: Alert) -> Investigation:
        deps = AnalystModel(alert=alert, runbook=self._runbook)
        result = self.agent.run_sync(
            f"Investigate the following alert:\n{alert.model_dump_json()}",
            deps=deps,
        )
        report = result.output
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
