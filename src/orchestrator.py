"""Coordinates agent communication for the investigation pipeline."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.agents.analyst_agent import AnalystAgent
from src.agents.data.base_data_agent import BaseDataAgent
from src.models import InvestigationModel
from src.runbook_registry import RunbookRegistry
from src.schemas.alert import Alert
from src.schemas.investigation import Investigation

if TYPE_CHECKING:
    from src.integrations.okta import OktaClient


class Orchestrator:
    def __init__(
        self,
        registry: RunbookRegistry,
        persistence: InvestigationModel,
        model: str,
        data_agents: list[BaseDataAgent],
        okta_client: OktaClient | None = None,
    ) -> None:
        self._registry = registry
        self._persistence = persistence
        self._model = model
        self._data_agents = data_agents
        self._okta_client = okta_client

    def investigate(self, alert: Alert) -> Investigation | None:
        runbook = self._registry.match(alert.type)
        if runbook is None:
            return None
        investigation = AnalystAgent(
            model=self._model,
            runbook=runbook,
            data_agents=self._data_agents,
            okta_client=self._okta_client,
        ).investigate(alert)
        self._persistence.save(investigation)
        return investigation
