"""Vulnerability Management analyst module — the second vertical."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.modules.vuln_mgmt.analyst import VulnAnalystAgent
from src.modules.vuln_mgmt.schemas.finding import Finding

if TYPE_CHECKING:
    from src.core.orchestration.capabilities import Capabilities
    from src.modules.vuln_mgmt.tools.intel import VulnIntelTool
    from src.schemas.investigation import Investigation


class VulnModule:
    """Triages vulnerability findings with a general-method VulnAnalystAgent.

    Selects its data source(s) from `Capabilities.data` by name and owns its
    vuln-intel tool; per-finding direction rides on the finding's `guidance` field.
    """

    name = "vuln_mgmt"
    input_type = Finding

    def __init__(
        self,
        model: str,
        intel: VulnIntelTool,
        data_sources: list[str],
    ) -> None:
        self._model = model
        self._intel = intel
        self._data_sources = data_sources

    def accepts(self, raw: dict) -> bool:
        """True if the payload is a valid vulnerability finding."""
        try:
            Finding(**raw)
            return True
        except Exception:
            return False

    def dedup_key(self, finding: Finding) -> str:
        """Review a finding once per (cve, asset, cvss) — a rescoring re-triages."""
        return f"{finding.cve}:{finding.asset}:{finding.cvss}"

    def investigate(self, finding: Finding, caps: Capabilities) -> Investigation:
        data_agents = [caps.data[n] for n in self._data_sources if n in caps.data]
        analyst = VulnAnalystAgent(
            model=self._model,
            data_agents=data_agents,
            intel=self._intel,
        )
        return analyst.investigate(finding)
