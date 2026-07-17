"""In-memory TriagePlatform — reference implementation for dev and tests.

Holds raw work items with a per-item status and records the actions Benny takes,
so the triage-loop can be exercised end-to-end without any external system.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.adapters.platforms.base import TriageStatus

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
        self._severity: dict[str, str] = {}
        self._comments: dict[str, list[str]] = {}
        self._cases: list[Case] = []
        self._case_seq = 0

    def fetch_open(self, limit: int = 50) -> list[dict]:
        open_items = [item for item_id, item in self._items.items() if self._status.get(item_id) == TriageStatus.OPEN]
        return open_items[:limit]

    def get(self, item_id: str) -> dict | None:
        return self._items.get(item_id)

    def comment(self, item_id: str, text: str) -> None:
        self._comments.setdefault(item_id, []).append(text)

    def set_severity(self, item_id: str, severity: str) -> None:
        self._severity[item_id] = severity

    def set_status(self, item_id: str, status: TriageStatus) -> None:
        self._status[item_id] = status

    def create_case(self, item_id: str, investigation: Investigation) -> str:
        self._case_seq += 1
        case_id = f"case-{self._case_seq}"
        self._cases.append(Case(case_id=case_id, item_id=item_id, investigation_id=investigation.id))
        return case_id

    def health_check(self) -> dict:
        return {
            "platform": "in-memory",
            "ok": True,
            "checks": {"alerts_read": "ok"},
            "open_alerts": len(self.fetch_open()),
        }

    # --- inspection helpers (for tests / dev) ---

    def status_of(self, item_id: str) -> TriageStatus:
        return self._status[item_id]

    def severity_of(self, item_id: str) -> str | None:
        return self._severity.get(item_id)

    def comments_of(self, item_id: str) -> list[str]:
        return self._comments.get(item_id, [])

    def cases(self) -> list[Case]:
        return list(self._cases)
