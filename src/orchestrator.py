"""Coordinates agent communication for the investigation pipeline."""

from src.agents.analyst_agent import AnalystAgent
from src.models import InvestigationModel
from src.runbook_registry import RunbookRegistry
from src.schemas.alert import Alert
from src.schemas.investigation import Investigation


class Orchestrator:
    def __init__(
        self,
        registry: RunbookRegistry,
        persistence: InvestigationModel,
        model: str,
    ) -> None:
        self._registry = registry
        self._persistence = persistence
        self._model = model

    def investigate(self, alert: Alert) -> Investigation | None:
        runbook = self._registry.match(alert.type)
        if runbook is None:
            return None
        investigation = AnalystAgent(model=self._model, runbook=runbook).investigate(
            alert
        )
        self._persistence.save(investigation)
        return investigation
