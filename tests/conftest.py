import os

# Tests must be hermetic: a developer's local config.toml (with secret-requiring
# sections) must not leak into the module-level Settings() built at import time.
# Pin CONFIG_FILE to a nonexistent path so config loads defaults; tests that need
# TOML behavior set CONFIG_FILE explicitly (see test_config.py).
os.environ.setdefault("CONFIG_FILE", "tests/.nonexistent-config.toml")

import uuid  # noqa: E402
from datetime import datetime, timezone  # noqa: E402
from unittest.mock import AsyncMock, MagicMock, patch  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from src.adapters.api.app import create_app  # noqa: E402
from src.modules.siem.schemas.incident_report import IncidentReport, Severity, Verdict  # noqa: E402
from src.schemas.investigation import Investigation, InvestigationStatus  # noqa: E402
from tests.harness.seeder.synthetic_db import SyntheticDataset  # noqa: E402


def _stub_investigation(alert_id: str, guidance_source: str | None = None) -> Investigation:
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
        guidance_source=guidance_source,
    )
    now = datetime.now(timezone.utc)
    return Investigation(
        id=str(uuid.uuid4()),
        alert_id=alert_id,
        status=InvestigationStatus.COMPLETE,
        severity=report.severity,
        verdict=report.verdict,
        guidance_source=guidance_source,
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

    class _Agent:
        model = "test:stub"

    class _Sqlite:
        name = "security_logs"
        db_path = str(tmp_path / "data.db")

    class _Data:
        sqlite = _Sqlite()
        elastic = None

    class _Vuln:
        db_path = str(tmp_path / "vuln.db")
        name = "asset_inventory"

    class _Config:
        persistence = _Persistence()
        agent = _Agent()
        data = _Data()
        vuln = _Vuln()
        kibana = None
        okta = None
        mcp_bearer_token = "test-mcp-token"

    app = create_app(cfg=_Config())
    mock_data_agent = MagicMock()
    mock_data_agent.name = "security_logs"
    mock_data_agent.routing_description = "Mock data source for tests."
    mock_data_agent.initialize = AsyncMock()
    with patch("src.adapters.api.app.SQLiteDataAgent", return_value=mock_data_agent):
        with (
            patch("src.modules.siem.module.AnalystAgent") as mock_cls,
            patch("src.modules.vuln_mgmt.module.VulnAnalystAgent") as vuln_cls,
        ):
            mock_cls.return_value.investigate.side_effect = lambda alert: _stub_investigation(alert.id)
            vuln_cls.return_value.investigate.side_effect = lambda finding: _stub_investigation(finding.id)
            with TestClient(app) as client:
                yield client
