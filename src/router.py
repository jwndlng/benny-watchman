"""Routes incoming alerts to the matching Runbook."""

from src.runbook.model import Runbook
from src.runbook.registry import RunbookRegistry
from src.schemas.alert import Alert


class Router:

    def __init__(self, registry: RunbookRegistry) -> None:
        self._registry = registry

    def route(self, alert: Alert) -> Runbook | None:
        return self._registry.match(alert.type)
