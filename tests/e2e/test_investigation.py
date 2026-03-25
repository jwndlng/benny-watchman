"""End-to-end investigation test — requires a real LLM API key.

Seeds a synthetic DB, fires an alert through the Orchestrator,
and asserts a valid IncidentReport comes back.

Run: AGENT_MODEL_API_KEY=... make test-e2e
"""

import os

import pytest

from src.models import ModelFactory
from src.orchestrator import Orchestrator
from src.runbook_registry import RunbookRegistry
from src.schemas.alert import Alert, Severity
from src.schemas.incident_report import IncidentReport
from src.schemas.investigation import InvestigationStatus
from tests.harness.seeder.synthetic_db import (
    BRUTE_FORCE_ATTACKER_IP,
    SyntheticDataset,
)

_HAS_API_KEY = bool(os.environ.get("AGENT_MODEL_API_KEY"))


@pytest.fixture
def orchestrator(tmp_path):
    """Wire up a real Orchestrator with a seeded data DB."""
    data_db = str(tmp_path / "data.db")
    SyntheticDataset(rows=200, seed=42).load(data_db)

    inv_db = str(tmp_path / "investigations.db")
    persistence = ModelFactory.investigations(db_path=inv_db)

    registry = RunbookRegistry()
    registry.load("runbooks")

    model = os.environ.get("AGENT_MODEL", "google-gla:gemini-3.1-flash-lite-preview")
    os.environ["DATA_BACKEND_DB_PATH"] = data_db

    return Orchestrator(registry, persistence, model=model)


@pytest.mark.e2e
@pytest.mark.skipif(not _HAS_API_KEY, reason="AGENT_MODEL_API_KEY not set")
def test_brute_force_investigation(orchestrator):
    """Full investigation: seed DB → submit brute-force alert → assert report."""
    alert = Alert(
        id="e2e-test-001",
        type="brute-force",
        title="Brute force detected",
        description=f"Repeated login failures from {BRUTE_FORCE_ATTACKER_IP}",
        severity=Severity.HIGH,
        source="test-harness",
        timestamp="2026-03-25T00:00:00Z",
    )

    investigation = orchestrator.investigate(alert)

    assert investigation is not None
    assert investigation.status == InvestigationStatus.COMPLETE
    assert investigation.alert_id == "e2e-test-001"
    assert investigation.report is not None

    report: IncidentReport = investigation.report
    assert report.alert_id == "e2e-test-001"
    assert report.runbook == "brute-force"
    assert 0.0 <= report.confidence <= 1.0
    assert len(report.findings) > 0
    assert len(report.summary) > 0
    assert len(report.affected_entities) > 0
    assert len(report.investigation_steps) > 0


@pytest.mark.e2e
@pytest.mark.skipif(not _HAS_API_KEY, reason="AGENT_MODEL_API_KEY not set")
def test_generic_fallback_investigation(orchestrator):
    """Unknown alert type falls back to the generic runbook."""
    alert = Alert(
        id="e2e-test-002",
        type="unknown-alert-type",
        title="Something happened",
        description="Unrecognised alert for fallback testing",
        severity=Severity.LOW,
        source="test-harness",
        timestamp="2026-03-25T00:00:00Z",
    )

    investigation = orchestrator.investigate(alert)

    assert investigation is not None
    assert investigation.status == InvestigationStatus.COMPLETE
    assert investigation.report is not None
    assert investigation.report.runbook == "generic"
