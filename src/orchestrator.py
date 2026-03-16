"""Coordinates agent communication for the investigation pipeline."""

from src.agents.analyst_agent import AnalystAgent
from src.persistence.base import PersistenceBackend
from src.router import Router
from src.runbook.registry import RunbookRegistry
from src.schemas.alert import Alert
from src.schemas.investigation import Investigation


class Orchestrator:
    def __init__(
        self,
        registry: RunbookRegistry,
        persistence: PersistenceBackend,
        model: str,
        db_path: str,
    ) -> None:
        self._router = Router(registry)
        self._persistence = persistence
        self._model = model
        self._db_path = db_path

    def investigate(self, alert: Alert) -> Investigation | None:
        runbook = self._router.route(alert)
        if runbook is None:
            return None
        investigation = AnalystAgent(
            model=self._model, runbook=runbook, db_path=self._db_path
        ).investigate(alert)
        self._persistence.save(investigation)
        return investigation
