"""Autonomously investigates alerts using a data sufficiency loop.

Bootstrapped by the Router with a Runbook (system prompt + scoped tool set).
Delegates data retrieval to DataAgent and enrichment to EnrichmentAgent.
Iterates until confident in a conclusion or the tool call limit is reached.
"""

import uuid
from datetime import datetime, timezone
from src.runbook.model import Runbook
from src.schemas.alert import Alert
from src.schemas.incident_report import IncidentReport, Severity, Verdict
from src.schemas.investigation import Investigation, InvestigationStatus


class AnalystAgent:
    def investigate(self, alert: Alert, runbook: Runbook) -> Investigation:
        # Stub — LLM investigation loop not yet implemented
        report = IncidentReport(
            alert_id=alert.id,
            severity=Severity.MEDIUM,
            verdict=Verdict.INCONCLUSIVE,
            confidence=0.0,
            summary="Stub investigation — agent not yet implemented.",
            findings=[],
            recommended_actions=[],
            detection_rule_improvements=[],
            runbook=runbook.name,
        )
        now = datetime.now(timezone.utc)
        return Investigation(
            id=str(uuid.uuid4()),
            alert_id=alert.id,
            status=InvestigationStatus.COMPLETE,
            severity=report.severity,
            verdict=report.verdict,
            runbook=runbook.name,
            created_at=now,
            completed_at=now,
            report=report,
        )
