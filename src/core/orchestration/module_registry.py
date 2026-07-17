"""Registry of analyst modules the orchestrator routes over.

Operates at the module (domain) level: it registers analyst modules by name and
resolves one for an incoming payload.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.orchestration.module import AnalystModule


class ModuleRegistry:
    """Registers analyst modules and resolves one for a request."""

    def __init__(self) -> None:
        self._modules: dict[str, AnalystModule] = {}

    def register(self, module: AnalystModule) -> None:
        """Register a module by name; raise on a duplicate name."""
        if module.name in self._modules:
            raise ValueError(f"Duplicate module name: {module.name}")
        self._modules[module.name] = module

    def get(self, name: str) -> AnalystModule | None:
        """Return the module registered under `name`, or None."""
        return self._modules.get(name)

    def resolve(self, raw: dict) -> AnalystModule | None:
        """Return the first module whose `accepts()` matches the payload, or None."""
        for module in self._modules.values():
            if module.accepts(raw):
                return module
        return None

    def list(self) -> list[AnalystModule]:
        """Return all registered modules."""
        return list(self._modules.values())
