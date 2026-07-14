"""Routes investigation requests to analyst modules (OrchestratorAgent)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import logfire

if TYPE_CHECKING:
    from src.core.orchestration.capabilities import Capabilities
    from src.core.orchestration.module_registry import ModuleRegistry
    from src.models import InvestigationModel
    from src.schemas.investigation import Investigation


class OrchestratorAgent:
    """Resolves an AnalystModule for a request and delegates the investigation.

    Two-speed routing: an explicit `hint` dispatches directly with no classifier;
    otherwise the module is resolved via each module's `accepts()`. Routes to a
    single module today — the return type leaves room for cross-module synthesis.
    """

    def __init__(
        self,
        registry: ModuleRegistry,
        persistence: InvestigationModel,
        capabilities: Capabilities,
    ) -> None:
        self._registry = registry
        self._persistence = persistence
        self._capabilities = capabilities

    def handle(self, raw: dict, hint: str | None = None) -> Investigation | None:
        """Resolve a module, run the investigation, persist and return it.

        Returns None when no module can handle the request.
        """
        module = self._registry.get(hint) if hint else self._registry.resolve(raw)
        if module is None:
            logfire.info("no module resolved for request", hint=hint)
            return None
        investigation = module.investigate(module.input_type(**raw), self._capabilities)
        if investigation is None:
            return None
        self._persistence.save(investigation)
        return investigation
