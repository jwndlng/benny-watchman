"""SIEM analyst module — the first vertical implementing the AnalystModule contract."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.modules.siem.alert import Alert
from src.modules.siem.analyst import AnalystAgent

if TYPE_CHECKING:
    from src.core.orchestration.capabilities import Capabilities
    from src.core.orchestration.runbook_registry import RunbookRegistry
    from src.schemas.investigation import Investigation


class SIEMModule:
    """Investigates SIEM alerts using runbook-scoped AnalystAgents.

    Runbook selection is internal to this module; the orchestrator only sees the
    `AnalystModule` contract. Capabilities (data sources, identity) are injected
    per investigation and forwarded to the AnalystAgent.
    """

    name = "siem"
    input_type = Alert

    def __init__(self, model: str, runbooks: RunbookRegistry) -> None:
        self._model = model
        self._runbooks = runbooks

    def accepts(self, raw: dict) -> bool:
        """True if the payload is a valid SIEM alert."""
        try:
            Alert(**raw)
            return True
        except Exception:  # noqa: BLE001
            return False

    def investigate(self, alert: Alert, caps: Capabilities) -> Investigation:
        """Match a runbook by alert type and run a scoped AnalystAgent."""
        runbook = self._runbooks.match(alert.type)
        analyst = AnalystAgent(
            model=self._model,
            runbook=runbook,
            data_agents=list(caps.data.values()),
            identity=caps.identity,
        )
        return analyst.investigate(alert)
