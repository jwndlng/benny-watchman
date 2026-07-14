"""Routes investigation requests to analyst modules (OrchestratorAgent)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import logfire

if TYPE_CHECKING:
    from src.core.orchestration.capabilities import Capabilities
    from src.core.orchestration.module_registry import ModuleRegistry
    from src.models import InvestigationModel
    from src.schemas.investigation import Investigation


@dataclass
class HandleResult:
    """Outcome of a handled request.

    `created` is True when a fresh investigation was run, False when an existing
    one was returned (dedup hit) or no module could handle the request.
    """

    investigation: Investigation | None
    created: bool


class OrchestratorAgent:
    """Resolves an AnalystModule for a request and delegates the investigation.

    Two-speed routing: an explicit `hint` dispatches directly with no classifier;
    otherwise the module is resolved via each module's `accepts()`. Enforces
    "review once": a request whose dedup key already has an investigation returns
    the stored one instead of re-running. Routes to a single module today — the
    return type leaves room for cross-module synthesis.
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

    def handle(self, raw: dict, hint: str | None = None) -> HandleResult:
        """Resolve a module, dedup, run if needed, persist, and return the result."""
        module = self._registry.get(hint) if hint else self._registry.resolve(raw)
        if module is None:
            logfire.info("no module resolved for request", hint=hint)
            return HandleResult(investigation=None, created=False)

        inp = module.input_type(**raw)
        key = f"{module.name}:{module.dedup_key(inp)}"

        existing = self._persistence.find_by_key(key)
        if existing is not None:
            logfire.info("dedup hit — returning existing investigation", key=key)
            return HandleResult(investigation=existing, created=False)

        investigation = module.investigate(inp, self._capabilities)
        if investigation is None:
            return HandleResult(investigation=None, created=False)
        investigation.key = key
        investigation.module = module.name
        self._persistence.save(investigation)
        return HandleResult(investigation=investigation, created=True)
