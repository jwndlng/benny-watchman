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
    ACKNOWLEDGED = "acknowledged"  # claimed — Benny is on it (or a human, post-escalation)
    CLOSED = "closed"  # terminal — triaged; carries a CloseReason


class CloseReason(str, Enum):
    """Why a work item was closed — mapped from the investigation disposition.

    Escalation is not a status: a `TRUE_POSITIVE` close still conveys urgency via
    the case (severity), while the alert lifecycle always ends `CLOSED`.
    """

    DUPLICATE = "duplicate"  # already triaged (dedup hit)
    FALSE_POSITIVE = "false_positive"
    BENIGN_POSITIVE = "benign_positive"  # benign / not-exploitable
    TRUE_POSITIVE = "true_positive"  # real — escalated via the case
    OTHER = "other"  # inconclusive / unknown disposition
    NONE = "none"  # closed without a reason


class CaseStatus(str, Enum):
    """Lifecycle of the case Benny opens for a work item.

    Mirrors the alert flow: open → in-progress (Benny is working it) → closed
    (Benny resolved it). An escalated case stays in-progress for a human. Values
    match the platform's case statuses (e.g. Kibana `open|in-progress|closed`).
    """

    OPEN = "open"
    IN_PROGRESS = "in-progress"
    CLOSED = "closed"


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

    def acknowledge(self, item_id: str) -> None:
        """Claim a work item for triage: move it OPEN → ACKNOWLEDGED.

        Called before investigation starts so the item leaves the open queue and
        signals that Benny is on it — an acknowledged item is not returned by
        `fetch_open` again while its investigation is in flight.
        """
        ...

    def comment(self, item_id: str, text: str) -> None:
        """Attach a triage comment to the work item (or its case)."""
        ...

    def set_severity(self, item_id: str, severity: str) -> None:
        """Set the assessed severity/priority for the work item."""
        ...

    def set_status(self, item_id: str, status: TriageStatus, reason: CloseReason | None = None) -> None:
        """Set the triage status; a terminal status removes it from the open queue.

        A terminal `CLOSED` status carries a `CloseReason` (the disposition-derived
        reason the item was closed); `reason` is ignored for non-terminal statuses.
        """
        ...

    def create_case(self, item_id: str, investigation: Investigation) -> str:
        """Open a case for traceability and return its id."""
        ...

    def set_case_status(self, item_id: str, status: CaseStatus) -> None:
        """Move the work item's case through its lifecycle (in-progress/closed).

        No-op if no case was created for the item. Benny moves a case to
        IN_PROGRESS after opening it and to CLOSED once the finding is resolved;
        an escalated case is left IN_PROGRESS for a human.
        """
        ...

    def health_check(self) -> dict:
        """Check connectivity and privileges without triaging or mutating anything.

        Returns a status dict: ``{"platform", "ok", "checks": {...}, "open_alerts"}``.
        """
        ...
