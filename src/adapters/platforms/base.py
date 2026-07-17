"""The TriagePlatform primitive — Benny's operational I/O boundary.

A platform supplies the work (alerts/findings to triage) and receives Benny's
actions (comment, disposition, case, status). It is the only surface that
mutates the outside world, so it is isolated, permission-scoped, and mockable.
Implementations live alongside this contract (memory.py now; elastic.py later).
Dependencies point inward only: platforms → core/schemas, never the reverse.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from src.schemas.investigation import Investigation


class TriageStatus(str, Enum):
    """Lifecycle of a work item within the platform."""

    OPEN = "open"  # needs triage
    ESCALATED = "escalated"  # actionable — left open for a human
    CLOSED = "closed"  # benign / false-positive — auto-closed by Benny


@runtime_checkable
class TriagePlatform(Protocol):
    """Intake + tracking + write-back against an operational system.

    Items produced by `fetch_open`/`get` carry any available investigation
    guidance in a `guidance` field, populated eagerly by the platform at fetch
    time — the analyst never pulls guidance itself (platforms → core only).
    """

    def fetch_open(self, limit: int = 50) -> list[dict]:
        """Return raw work items still needing triage (status OPEN).

        Each item has an 'id' and carries a `guidance` field when the source
        provides investigation guidance for it.
        """
        ...

    def get(self, item_id: str) -> dict | None:
        """Return the raw work item by id (with `guidance` when available), or None."""
        ...

    def comment(self, item_id: str, text: str) -> None:
        """Attach a triage comment to the work item (or its case)."""
        ...

    def set_severity(self, item_id: str, severity: str) -> None:
        """Set the assessed severity/priority for the work item."""
        ...

    def set_status(self, item_id: str, status: TriageStatus) -> None:
        """Set the triage status; a terminal status removes it from the open queue."""
        ...

    def create_case(self, item_id: str, investigation: Investigation) -> str:
        """Open a case for traceability and return its id."""
        ...

    def health_check(self) -> dict:
        """Check connectivity and privileges without triaging or mutating anything.

        Returns a status dict: ``{"platform", "ok", "checks": {...}, "open_alerts"}``.
        """
        ...
