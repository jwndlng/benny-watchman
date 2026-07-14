import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.modules.siem.incident_report import IncidentReport, Severity, Verdict
from src.schemas.investigation import Investigation, InvestigationStatus
from tests.harness.seeder.synthetic_db import SyntheticDataset


def _stub_investigation(alert_id: str, runbook_name: str) -> Investigation:
    report = IncidentReport(
        alert_id=alert_id,
        severity=Severity.MEDIUM,
        verdict=Verdict.INCONCLUSIVE,
        confidence=0.0,
        summary="Stub investigation — mocked for tests.",
        affected_entities=[],
        timeline=[],
        investigation_steps=[],
        scope="unknown",
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
        report=report.model_dump(mode="json"),
    )


@pytest.fixture
def seeded_db(tmp_path) -> str:
    db_path = str(tmp_path / "data.db")
    SyntheticDataset(rows=200, seed=42).load(db_path)
    return db_path


@pytest.fixture
def client(tmp_path):
    class _Persistence:
        engine = "sqlite"
        db_path = str(tmp_path / "test.db")

    class _Runbooks:
        path = "src/modules/siem/runbooks"

    class _Agent:
        model = "test:stub"

    class _Data:
        db_path = str(tmp_path / "data.db")
        name = "security_logs"

    class _Vuln:
        db_path = str(tmp_path / "vuln.db")
        runbooks_path = "src/modules/vuln_mgmt/runbooks"
        name = "asset_inventory"

    class _Config:
        persistence = _Persistence()
        runbooks = _Runbooks()
        agent = _Agent()
        data = _Data()
        vuln = _Vuln()
        elastic = None
        okta = None
        mcp_bearer_token = "test-mcp-token"

    app = create_app(cfg=_Config())
    mock_data_agent = MagicMock()
    mock_data_agent.name = "security_logs"
    mock_data_agent.routing_description = "Mock data source for tests."
    mock_data_agent.initialize = AsyncMock()
    with patch("src.api.app.SQLiteDataAgent", return_value=mock_data_agent):
        with (
            patch("src.modules.siem.module.AnalystAgent") as mock_cls,
            patch("src.modules.vuln_mgmt.module.VulnAnalystAgent") as vuln_cls,
        ):
            mock_cls.return_value.investigate.side_effect = lambda alert: (
                _stub_investigation(alert.id, "generic")
            )
            vuln_cls.return_value.investigate.side_effect = lambda finding: (
                _stub_investigation(finding.id, "generic")
            )
            with TestClient(app) as client:
                yield client
