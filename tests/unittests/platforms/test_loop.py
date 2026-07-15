"""Unit tests for the triage-loop (run_once)."""

import pathlib
from datetime import datetime, timezone

from src.core.orchestration.orchestrator import HandleResult
from src.platforms.base import TriageStatus
from src.platforms.loop import run_once
from src.platforms.memory import InMemoryTriagePlatform
from src.schemas.investigation import Investigation, InvestigationStatus
from src.schemas.outcome import Outcome


def _investigation(
    item_id: str, disposition: str, priority: str = "high"
) -> Investigation:
    now = datetime.now(timezone.utc)
    return Investigation(
        id=f"inv-{item_id}",
        alert_id=item_id,
        status=InvestigationStatus.COMPLETE,
        outcome=Outcome(disposition=disposition, priority=priority),
        report={"summary": f"summary for {item_id}"},
        created_at=now,
        completed_at=now,
    )


class _FakeOrchestrator:
    """Returns a preset HandleResult per work-item id."""

    def __init__(self, results: dict[str, HandleResult]) -> None:
        self._results = results

    def handle(self, raw: dict, hint: str) -> HandleResult:
        return self._results[raw["id"]]


def test_benign_is_closed_and_true_positive_is_escalated():
    platform = InMemoryTriagePlatform([{"id": "a1"}, {"id": "a2"}])
    orch = _FakeOrchestrator(
        {
            "a1": HandleResult(_investigation("a1", "false_positive"), created=True),
            "a2": HandleResult(_investigation("a2", "true_positive"), created=True),
        }
    )

    handled = run_once(orch, platform, hint="siem")

    assert len(handled) == 2
    assert platform.status_of("a1") == TriageStatus.CLOSED
    assert platform.status_of("a2") == TriageStatus.ESCALATED
    # case-always + write-back for both
    assert len(platform.cases()) == 2
    assert platform.severity_of("a1") == "high"
    assert platform.comments_of("a1")
    assert platform.comments_of("a2")
    # both are now out of the open queue
    assert platform.fetch_open() == []


def test_dedup_and_unresolved_are_skipped():
    platform = InMemoryTriagePlatform([{"id": "a1"}, {"id": "a2"}])
    orch = _FakeOrchestrator(
        {
            "a1": HandleResult(_investigation("a1", "true_positive"), created=False),
            "a2": HandleResult(None, created=False),
        }
    )

    handled = run_once(orch, platform, hint="siem")

    assert handled == []
    assert platform.cases() == []
    assert platform.comments_of("a1") == []
    assert platform.status_of("a1") == TriageStatus.OPEN
    assert platform.status_of("a2") == TriageStatus.OPEN


def test_core_does_not_import_platforms():
    """Dependency direction: nothing under src/core imports src/platforms."""
    offenders = [
        str(path)
        for path in pathlib.Path("src/core").rglob("*.py")
        if "src.platforms" in path.read_text()
    ]
    assert offenders == [], f"core must not import platforms: {offenders}"
