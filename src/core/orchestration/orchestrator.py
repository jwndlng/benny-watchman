"""Routes investigation requests to analyst modules (OrchestratorAgent)."""

from __future__ import annotations

from dataclasses import dataclass

import logfire

from src.core.orchestration.capabilities import Capabilities
from src.core.orchestration.module_registry import ModuleRegistry
from src.core.ports.persistence import InvestigationStore
from src.schemas.investigation import Investigation


@dataclass
class HandleResult:
    """Outcome of a handled request.

    `created` is True when a brand-new record was persisted, False when an
    existing record for the key was returned (dedup) or updated in place, or no
    module could handle the request.
    """

    investigation: Investigation | None
    created: bool


class OrchestratorAgent:
    """Resolves an AnalystModule for a request and delegates the investigation.

    Two-speed routing: an explicit `hint` dispatches directly with no classifier;
    otherwise the module is resolved via each module's `accepts()`. "Review once"
    is available via `dedup` (default on, e.g. the /investigate API) but opt-out:
    the triage loop passes `dedup=False` because the platform owns review-once and
    the investigations store is context, not a triage gate. Routes to a single
    module today — the return type leaves room for cross-module synthesis.
    """

    def __init__(
        self,
        registry: ModuleRegistry,
        persistence: InvestigationStore,
        capabilities: Capabilities,
    ) -> None:
        self._registry = registry
        self._persistence = persistence
        self._capabilities = capabilities

    def handle(self, raw: dict, hint: str | None = None, *, dedup: bool = True) -> HandleResult:
        """Resolve a module, optionally dedup, run the analyst, upsert, and return it.

        With `dedup=True` (default — the /investigate API) an existing investigation
        for the key is returned without re-running ("review once"). With
        `dedup=False` (the triage loop, where the platform owns review-once) the
        analyst always runs and the record is upserted by key (updating any existing
        one) — the store is context for lookups/MCP, not a triage gate.
        """
        module = self._registry.get(hint) if hint else self._registry.resolve(raw)
        if module is None:
            logfire.info("no module resolved for request", hint=hint)
            return HandleResult(investigation=None, created=False)

        inp = module.input_type(**raw)
        key = f"{module.name}:{module.dedup_key(inp)}"
        existing = self._persistence.find_by_key(key)
        if dedup and existing is not None:
            logfire.info("dedup hit — returning existing investigation", key=key)
            return HandleResult(investigation=existing, created=False)

        investigation = module.investigate(inp, self._capabilities)
        if investigation is None:
            return HandleResult(investigation=None, created=False)
        investigation.key = key
        investigation.module = module.name
        if existing is not None:
            investigation.id = existing.id  # upsert: update the existing context record in place
        self._persistence.save(investigation)
        return HandleResult(investigation=investigation, created=existing is None)
