"""Unit tests for the module contract, registry, and OrchestratorAgent."""

from unittest.mock import MagicMock

import pytest

from src.core.orchestration.capabilities import Capabilities
from src.core.orchestration.module_registry import ModuleRegistry
from src.core.orchestration.orchestrator import OrchestratorAgent
from src.modules.siem.module import SIEMModule

VALID_ALERT = {
    "id": "alert-001",
    "type": "brute-force",
    "title": "Multiple failed logins",
    "description": "50 failed login attempts in 5 minutes",
    "severity": "high",
    "source": "splunk",
    "timestamp": "2026-03-13T10:00:00Z",
}


class _StubInput:
    def __init__(self, **kw: object) -> None:
        self.__dict__.update(kw)


class _StubModule:
    input_type = _StubInput

    def __init__(self, name: str = "stub", accepts: bool = True) -> None:
        self.name = name
        self._accepts = accepts
        self.investigation = MagicMock()

    def accepts(self, raw: dict) -> bool:
        return self._accepts

    def dedup_key(self, inp: object) -> str:
        return "k"

    def investigate(self, inp: object, caps: Capabilities) -> object:
        return self.investigation


def _fresh_persistence() -> MagicMock:
    """A persistence mock that reports no existing investigation (fresh path)."""
    persistence = MagicMock()
    persistence.find_by_key.return_value = None
    return persistence


def test_registry_register_and_get():
    registry = ModuleRegistry()
    module = _StubModule()
    registry.register(module)
    assert registry.get("stub") is module
    assert registry.get("unknown") is None


def test_registry_resolve_by_accepts():
    registry = ModuleRegistry()
    module = _StubModule(accepts=True)
    registry.register(module)
    assert registry.resolve({"x": 1}) is module


def test_registry_resolve_none_when_nothing_accepts():
    registry = ModuleRegistry()
    registry.register(_StubModule(accepts=False))
    assert registry.resolve({"x": 1}) is None


def test_registry_duplicate_name_raises():
    registry = ModuleRegistry()
    registry.register(_StubModule())
    with pytest.raises(ValueError):
        registry.register(_StubModule())


def test_orchestrator_hint_dispatches_and_persists():
    registry = ModuleRegistry()
    module = _StubModule()
    registry.register(module)
    persistence = _fresh_persistence()
    orch = OrchestratorAgent(registry, persistence, Capabilities())

    result = orch.handle({"a": 1}, hint="stub")

    assert result.investigation is module.investigation
    assert result.created is True
    persistence.save.assert_called_once_with(module.investigation)


def test_orchestrator_unresolved_returns_none():
    persistence = _fresh_persistence()
    orch = OrchestratorAgent(ModuleRegistry(), persistence, Capabilities())
    result = orch.handle({"a": 1}, hint="missing")
    assert result.investigation is None
    assert result.created is False
    persistence.save.assert_not_called()


def test_orchestrator_dedup_returns_existing_without_rerun():
    registry = ModuleRegistry()
    registry.register(_StubModule())
    persistence = MagicMock()
    existing = MagicMock()
    persistence.find_by_key.return_value = existing
    orch = OrchestratorAgent(registry, persistence, Capabilities())

    result = orch.handle({"a": 1}, hint="stub")

    assert result.investigation is existing
    assert result.created is False
    persistence.save.assert_not_called()


def test_siem_module_accepts_valid_alert_only():
    runbooks = MagicMock()
    module = SIEMModule(model="test:stub", runbooks=runbooks)
    assert module.accepts(VALID_ALERT) is True
    assert module.accepts({"id": "only"}) is False


def test_siem_module_dedup_key_is_alert_id():
    from src.modules.siem.alert import Alert

    module = SIEMModule(model="test:stub", runbooks=MagicMock())
    assert module.dedup_key(Alert(**VALID_ALERT)) == "alert-001"
