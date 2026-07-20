"""In-memory TriagePlatform — reference implementation for dev and tests.

Holds raw work items with a per-item status and records the actions Benny takes,
so the triage-loop can be exercised end-to-end without any external system.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.adapters.platforms.base import CaseStatus, CloseReason, TriageStatus

if TYPE_CHECKING:
    from src.schemas.investigation import Investigation


@dataclass
class Case:
    """A case opened for a work item."""

    case_id: str
    item_id: str
    investigation_id: str


class InMemoryTriagePlatform:
    """A TriagePlatform backed entirely by in-memory state."""

    def __init__(self, items: list[dict]) -> None:
        self._items: dict[str, dict] = {item["id"]: item for item in items}
        self._status: dict[str, TriageStatus] = {item["id"]: TriageStatus.OPEN for item in items}
        self._reason: dict[str, CloseReason | None] = {}
        self._severity: dict[str, str] = {}
        self._comments: dict[str, list[str]] = {}
        self._cases: list[Case] = []
        self._case_status: dict[str, CaseStatus] = {}
        self._case_seq = 0

    def fetch_open(self, limit: int = 50) -> list[dict]:
        """Return open work items, capped at `limit`."""
        open_items = [item for item_id, item in self._items.items() if self._status.get(item_id) == TriageStatus.OPEN]
        return open_items[:limit]

    def get(self, item_id: str) -> dict | None:
        """Return the raw work item by id, or None."""
        return self._items.get(item_id)

    def acknowledge(self, item_id: str) -> None:
        """Claim a work item: OPEN → ACKNOWLEDGED (drops it from the open queue)."""
        self._status[item_id] = TriageStatus.ACKNOWLEDGED

    def comment(self, item_id: str, text: str) -> None:
        """Record a comment against the work item."""
        self._comments.setdefault(item_id, []).append(text)

    def set_severity(self, item_id: str, severity: str) -> None:
        """Set the work item's severity."""
        self._severity[item_id] = severity

    def set_status(self, item_id: str, status: TriageStatus, reason: CloseReason | None = None) -> None:
        """Set the work item's triage status, recording the close reason when CLOSED."""
        self._status[item_id] = status
        if status == TriageStatus.CLOSED:
            self._reason[item_id] = reason

    def create_case(self, item_id: str, investigation: Investigation) -> str:
        """Open a case for the work item and return its id."""
        self._case_seq += 1
        case_id = f"case-{self._case_seq}"
        self._cases.append(Case(case_id=case_id, item_id=item_id, investigation_id=investigation.id))
        self._case_status[item_id] = CaseStatus.OPEN
        return case_id

    def set_case_status(self, item_id: str, status: CaseStatus) -> None:
        """Move the item's case to a new status; no-op if it has no case."""
        if item_id in self._case_status:
            self._case_status[item_id] = status

    def health_check(self) -> dict:
        """Report platform reachability and open-alert count."""
        return {
            "platform": "in-memory",
            "ok": True,
            "checks": {"alerts_read": "ok"},
            "open_alerts": len(self.fetch_open()),
        }

    # --- inspection helpers (for tests / dev) ---

    def status_of(self, item_id: str) -> TriageStatus:
        """Return the current triage status of a work item."""
        return self._status[item_id]

    def reason_of(self, item_id: str) -> CloseReason | None:
        """Return the recorded close reason of a work item, or None."""
        return self._reason.get(item_id)

    def severity_of(self, item_id: str) -> str | None:
        """Return the recorded severity of a work item, or None."""
        return self._severity.get(item_id)

    def comments_of(self, item_id: str) -> list[str]:
        """Return the comments recorded against a work item."""
        return self._comments.get(item_id, [])

    def cases(self) -> list[Case]:
        """Return the cases opened this run."""
        return list(self._cases)

    def case_status_of(self, item_id: str) -> CaseStatus | None:
        """Return the current status of the item's case, or None if it has no case."""
        return self._case_status.get(item_id)
