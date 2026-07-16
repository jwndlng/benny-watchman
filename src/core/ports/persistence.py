"""Persistence port — the investigation-store interface `core` depends on.

Defined here (not in adapters) so the orchestrator dares not reach outward for its
persistence type. `adapters.persistence.InvestigationModel` satisfies it structurally.
"""

from typing import Protocol

from src.schemas.investigation import Investigation


class InvestigationStore(Protocol):
    """What the orchestrator needs from investigation persistence."""

    def find_by_key(self, key: str) -> Investigation | None:
        """Return the investigation with the given dedup key, or None."""
        ...

    def save(self, item: Investigation) -> None:
        """Insert or replace an investigation by id."""
        ...
