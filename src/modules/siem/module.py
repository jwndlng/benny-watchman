"""SIEM analyst module — the first vertical implementing the AnalystModule contract."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.modules.siem.alert import Alert
from src.modules.siem.analyst import AnalystAgent

if TYPE_CHECKING:
    from src.core.orchestration.capabilities import Capabilities
    from src.schemas.investigation import Investigation


class SIEMModule:
    """Investigates SIEM alerts with a general-method AnalystAgent.

    The orchestrator only sees the `AnalystModule` contract. Capabilities (data
    sources, identity) are injected per investigation and forwarded to the
    AnalystAgent; per-alert direction rides on the alert's `guidance` field.
    """

    name = "siem"
    input_type = Alert

    def __init__(self, model: str, data_sources: list[str]) -> None:
        self._model = model
        self._data_sources = data_sources

    def accepts(self, raw: dict) -> bool:
        """True if the payload is a valid SIEM alert."""
        try:
            Alert(**raw)
            return True
        except Exception:  # noqa: BLE001
            return False

    def dedup_key(self, alert: Alert) -> str:
        """Each alert firing is reviewed once, keyed by its id."""
        return alert.id

    def investigate(self, alert: Alert, caps: Capabilities) -> Investigation:
        """Run the SIEM AnalystAgent over the injected capabilities."""
        data_agents = [caps.data[n] for n in self._data_sources if n in caps.data]
        analyst = AnalystAgent(
            model=self._model,
            data_agents=data_agents,
            identity=caps.identity,
        )
        return analyst.investigate(alert)
