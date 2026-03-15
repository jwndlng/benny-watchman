"""Coordinates agent communication for the investigation pipeline."""

from src.agents.analyst_agent import AnalystAgent
from src.persistence.base import PersistenceBackend
from src.router import Router
from src.runbook.registry import RunbookRegistry
from src.schemas.alert import Alert
from src.schemas.investigation import Investigation


class Orchestrator:

    def __init__(self, registry: RunbookRegistry, persistence: PersistenceBackend) -> None:
        self._router = Router(registry)
        self._analyst = AnalystAgent()
        self._persistence = persistence

    def investigate(self, alert: Alert) -> Investigation | None:
        runbook = self._router.route(alert)
        if runbook is None:
            return None
        investigation = self._analyst.investigate(alert, runbook)
        self._persistence.save(investigation)
        return investigation
