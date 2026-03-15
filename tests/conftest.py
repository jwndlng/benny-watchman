import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from src.api.app import create_app
from src.schemas.incident_report import IncidentReport, Severity, Verdict
from src.schemas.investigation import Investigation, InvestigationStatus


def _stub_investigation(alert_id: str, runbook_name: str) -> Investigation:
    report = IncidentReport(
        alert_id=alert_id,
        severity=Severity.MEDIUM,
        verdict=Verdict.INCONCLUSIVE,
        confidence=0.0,
        summary="Stub investigation — mocked for tests.",
        findings=[],
        recommended_actions=[],
        detection_rule_improvements=[],
        runbook=runbook_name,
    )
    now = datetime.now(timezone.utc)
    return Investigation(
        id=str(uuid.uuid4()),
        alert_id=alert_id,
        status=InvestigationStatus.COMPLETE,
        severity=report.severity,
        verdict=report.verdict,
        runbook=runbook_name,
        created_at=now,
        completed_at=now,
        report=report,
    )


@pytest.fixture
def client(tmp_path):
    class _Persistence:
        engine = "sqlite"
        db_path = str(tmp_path / "test.db")

    class _Runbooks:
        path = "runbooks"

    class _Agent:
        model = "test:stub"

    class _Config:
        persistence = _Persistence()
        runbooks = _Runbooks()
        agent = _Agent()

    app = create_app(cfg=_Config())
    app.config["TESTING"] = True
    with app.test_client() as client:
        with patch("src.orchestrator.AnalystAgent") as mock_cls:
            mock_cls.return_value.investigate.side_effect = (
                lambda alert: _stub_investigation(alert.id, "generic")
            )
            yield client
