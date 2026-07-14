"""Vulnerability Management analyst module — the second vertical."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.modules.vuln_mgmt.analyst import VulnAnalystAgent
from src.modules.vuln_mgmt.finding import Finding

if TYPE_CHECKING:
    from src.core.orchestration.capabilities import Capabilities
    from src.core.orchestration.runbook_registry import RunbookRegistry
    from src.modules.vuln_mgmt.intel import VulnIntelCapability
    from src.schemas.investigation import Investigation


class VulnModule:
    """Triages vulnerability findings using runbook-scoped VulnAnalystAgents.

    Selects its data source(s) from `Capabilities.data` by name and owns its
    vuln-intel tool; runbook selection is internal.
    """

    name = "vuln_mgmt"
    input_type = Finding

    def __init__(
        self,
        model: str,
        runbooks: RunbookRegistry,
        intel: VulnIntelCapability,
        data_sources: list[str],
    ) -> None:
        self._model = model
        self._runbooks = runbooks
        self._intel = intel
        self._data_sources = data_sources

    def accepts(self, raw: dict) -> bool:
        """True if the payload is a valid vulnerability finding."""
        try:
            Finding(**raw)
            return True
        except Exception:  # noqa: BLE001
            return False

    def dedup_key(self, finding: Finding) -> str:
        """Review a finding once per (cve, asset, cvss) — a rescoring re-triages."""
        return f"{finding.cve}:{finding.asset}:{finding.cvss}"

    def investigate(self, finding: Finding, caps: Capabilities) -> Investigation:
        runbook = self._runbooks.match(finding.type)
        data_agents = [caps.data[n] for n in self._data_sources if n in caps.data]
        analyst = VulnAnalystAgent(
            model=self._model,
            runbook=runbook,
            data_agents=data_agents,
            intel=self._intel,
        )
        return analyst.investigate(finding)
