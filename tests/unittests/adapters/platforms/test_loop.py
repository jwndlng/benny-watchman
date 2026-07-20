"""Unit tests for the triage-loop (run_once)."""

import pathlib
from datetime import datetime, timezone

from src.core.orchestration.orchestrator import HandleResult
from src.adapters.platforms.base import CaseStatus, CloseReason, TriageStatus
from src.adapters.platforms.loop import run_once
from src.adapters.platforms.memory import InMemoryTriagePlatform
from src.schemas.investigation import Investigation, InvestigationStatus
from src.schemas.outcome import Outcome


def _investigation(item_id: str, disposition: str, priority: str = "high") -> Investigation:
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
        self.dedup_flags: list[bool] = []

    def handle(self, raw: dict, hint: str, dedup: bool = True) -> HandleResult:
        self.dedup_flags.append(dedup)
        return self._results[raw["id"]]


def test_both_dispositions_close_with_a_reason():
    platform = InMemoryTriagePlatform([{"id": "a1"}, {"id": "a2"}])
    orch = _FakeOrchestrator(
        {
            "a1": HandleResult(_investigation("a1", "false_positive"), created=True),
            "a2": HandleResult(_investigation("a2", "true_positive"), created=True),
        }
    )

    handled = run_once(orch, platform, hint="siem")

    assert len(handled) == 2
    # every triaged alert ends CLOSED, with a disposition-derived reason
    assert platform.status_of("a1") == TriageStatus.CLOSED
    assert platform.reason_of("a1") == CloseReason.FALSE_POSITIVE
    assert platform.status_of("a2") == TriageStatus.CLOSED
    assert platform.reason_of("a2") == CloseReason.TRUE_POSITIVE
    # case-always + write-back for both; true-positive escalates via case severity
    assert len(platform.cases()) == 2
    assert platform.severity_of("a1") == "high"
    assert platform.severity_of("a2") == "high"
    assert platform.comments_of("a1")
    assert platform.comments_of("a2")
    # case lifecycle: benign is resolved → case CLOSED; true-positive is escalated
    # → case left IN_PROGRESS for a human
    assert platform.case_status_of("a1") == CaseStatus.CLOSED
    assert platform.case_status_of("a2") == CaseStatus.IN_PROGRESS
    # both are now out of the open queue
    assert platform.fetch_open() == []


def test_item_is_acknowledged_before_handle():
    platform = InMemoryTriagePlatform([{"id": "a1"}])
    seen_status: dict[str, TriageStatus] = {}

    class _CapturingOrch:
        def handle(self, raw: dict, hint: str, dedup: bool = True) -> HandleResult:
            seen_status[raw["id"]] = platform.status_of(raw["id"])
            return HandleResult(_investigation(raw["id"], "false_positive"), created=True)

    run_once(_CapturingOrch(), platform, hint="siem")

    assert seen_status["a1"] == TriageStatus.ACKNOWLEDGED


def test_limit_bounds_how_many_are_triaged():
    platform = InMemoryTriagePlatform([{"id": "a1"}, {"id": "a2"}, {"id": "a3"}])
    orch = _FakeOrchestrator(
        {item: HandleResult(_investigation(item, "false_positive"), created=True) for item in ("a1", "a2", "a3")}
    )

    handled = run_once(orch, platform, hint="siem", limit=1)

    assert len(handled) == 1
    assert len(platform.cases()) == 1
    # two alerts remain open (not all triaged)
    assert len(platform.fetch_open()) == 2


def test_loop_disables_db_dedup():
    # the loop relies on the platform for review-once, so it calls handle with
    # dedup=False (the DB is a context store, not a triage gate).
    platform = InMemoryTriagePlatform([{"id": "a1"}])
    orch = _FakeOrchestrator({"a1": HandleResult(_investigation("a1", "false_positive"), created=True)})

    run_once(orch, platform, hint="siem")

    assert orch.dedup_flags == [False]


def test_investigation_is_written_back_regardless_of_created_flag():
    # with DB dedup off, an "updated existing record" (created=False) is still a
    # real investigation for a still-open alert and must be written back.
    platform = InMemoryTriagePlatform([{"id": "a1"}, {"id": "a2"}])
    orch = _FakeOrchestrator(
        {
            "a1": HandleResult(_investigation("a1", "false_positive"), created=False),
            "a2": HandleResult(None, created=False),
        }
    )

    handled = run_once(orch, platform, hint="siem")

    # a1 has an investigation → written back and closed with a reason, case-always
    assert len(handled) == 1
    assert platform.status_of("a1") == TriageStatus.CLOSED
    assert platform.reason_of("a1") == CloseReason.FALSE_POSITIVE
    assert len(platform.cases()) == 1
    # a2 has no module/investigation → left ACKNOWLEDGED, no case
    assert platform.status_of("a2") == TriageStatus.ACKNOWLEDGED
    assert platform.cases()[0].item_id == "a1"


def test_core_does_not_import_platforms():
    """Dependency direction: nothing under src/core imports src/platforms."""
    offenders = [
        str(path) for path in pathlib.Path("src/core").rglob("*.py") if "src.adapters.platforms" in path.read_text()
    ]
    assert offenders == [], f"core must not import platforms: {offenders}"
