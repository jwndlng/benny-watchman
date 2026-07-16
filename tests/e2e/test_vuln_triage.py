"""End-to-end VM triage test — requires a real LLM API key.

Seeds a synthetic asset inventory, fires a finding through the OrchestratorAgent
+ VM module, and asserts a valid VulnTriageReport comes back.

Run: AGENT_MODEL_API_KEY=... make test-e2e
"""

import asyncio
import os

import pytest

from src.capabilities.subagents.data.sqlite_data_agent import SQLiteDataAgent
from src.core.orchestration.capabilities import Capabilities
from src.core.orchestration.module_registry import ModuleRegistry
from src.core.orchestration.orchestrator import OrchestratorAgent
from src.core.orchestration.runbook_registry import RunbookRegistry
from src.adapters.persistence import ModelFactory
from src.modules.vuln_mgmt.schemas.finding import Finding
from src.modules.vuln_mgmt.tools.intel import VulnIntelCapability
from src.modules.vuln_mgmt.module import VulnModule
from src.schemas.investigation import InvestigationStatus
from tests.harness.seeder.asset_db import PLANTED_ASSET, PLANTED_CVE, AssetDataset

_HAS_API_KEY = bool(os.environ.get("AGENT_MODEL_API_KEY"))


@pytest.fixture
def orchestrator(tmp_path):
    """Wire up a real OrchestratorAgent (VM module) with a seeded asset DB."""
    asset_db = str(tmp_path / "vuln.db")
    AssetDataset().load(asset_db)

    persistence = ModelFactory.investigations(db_path=str(tmp_path / "inv.db"))
    runbooks = RunbookRegistry()
    runbooks.load("src/modules/vuln_mgmt/runbooks")

    model = os.environ.get("AGENT_MODEL", "google-gla:gemini-3.1-flash-lite-preview")

    asset_agent = SQLiteDataAgent(name="asset_inventory", model=model, db_path=asset_db)
    asyncio.run(asset_agent.initialize())
    capabilities = Capabilities(data={asset_agent.name: asset_agent})

    registry = ModuleRegistry()
    registry.register(
        VulnModule(
            model=model,
            runbooks=runbooks,
            intel=VulnIntelCapability(),
            data_sources=["asset_inventory"],
        )
    )
    return OrchestratorAgent(registry, persistence, capabilities)


@pytest.mark.e2e
@pytest.mark.skipif(not _HAS_API_KEY, reason="AGENT_MODEL_API_KEY not set")
def test_rce_finding_triage(orchestrator):
    """Full triage: seed assets → submit an RCE finding → assert a VM report."""
    finding = Finding(
        id="e2e-vuln-001",
        type="remote-code-execution",
        cve=PLANTED_CVE,
        asset=PLANTED_ASSET,
        cvss=9.8,
        title="Unauthenticated RCE",
        description=f"RCE affecting {PLANTED_ASSET}",
        source="test-harness",
        detected_at="2026-03-25T00:00:00Z",
    )

    result = orchestrator.handle(finding.model_dump(), hint="vuln_mgmt")

    assert result.investigation is not None
    inv = result.investigation
    assert inv.status == InvestigationStatus.COMPLETE
    assert inv.alert_id == "e2e-vuln-001"
    assert inv.module == "vuln_mgmt"
    assert inv.report is not None
    assert inv.report["finding_id"] == "e2e-vuln-001"
    assert 0.0 <= inv.report["confidence"] <= 1.0
    assert inv.outcome is not None
