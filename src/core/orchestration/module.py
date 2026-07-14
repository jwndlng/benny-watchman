"""The AnalystModule contract — one implementation per triage domain.

A module owns its input type and knows how to investigate it end-to-end using
the shared `Capabilities`. Adding a triage domain means adding a module, not
modifying core code. `dedup_key` is intentionally absent — it is introduced by
the `investigation-idempotency` change, the one that consumes it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from src.core.orchestration.capabilities import Capabilities
    from src.schemas.investigation import Investigation


@runtime_checkable
class AnalystModule(Protocol):
    """A triage domain: declares its input type and how to investigate it."""

    name: str
    input_type: type

    def accepts(self, raw: dict) -> bool:
        """Return True if this module can handle the given raw payload."""
        ...

    def investigate(self, inp: object, caps: Capabilities) -> Investigation:
        """Investigate a validated input and return the resulting Investigation."""
        ...
