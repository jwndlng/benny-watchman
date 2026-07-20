"""Unit tests for InMemoryTriagePlatform."""

from datetime import datetime, timezone

from src.adapters.platforms.base import CaseStatus, CloseReason, TriagePlatform, TriageStatus
from src.adapters.platforms.memory import InMemoryTriagePlatform
from src.schemas.investigation import Investigation, InvestigationStatus


def _investigation(item_id: str) -> Investigation:
    now = datetime.now(timezone.utc)
    return Investigation(id=f"inv-{item_id}", alert_id=item_id, status=InvestigationStatus.COMPLETE, created_at=now)


def test_satisfies_the_protocol():
    platform = InMemoryTriagePlatform([])
    assert isinstance(platform, TriagePlatform)
    assert callable(platform.acknowledge)


def test_fetch_open_returns_open_items_with_ids():
    platform = InMemoryTriagePlatform([{"id": "a1"}, {"id": "a2"}])
    ids = {item["id"] for item in platform.fetch_open()}
    assert ids == {"a1", "a2"}


def test_acknowledge_claims_item_and_drops_from_open_queue():
    platform = InMemoryTriagePlatform([{"id": "a1"}, {"id": "a2"}])
    platform.acknowledge("a1")
    assert platform.status_of("a1") == TriageStatus.ACKNOWLEDGED
    assert {item["id"] for item in platform.fetch_open()} == {"a2"}


def test_close_records_reason_and_drops_from_open_queue():
    platform = InMemoryTriagePlatform([{"id": "a1"}, {"id": "a2"}])
    platform.set_status("a1", TriageStatus.CLOSED, reason=CloseReason.FALSE_POSITIVE)
    assert platform.status_of("a1") == TriageStatus.CLOSED
    assert platform.reason_of("a1") == CloseReason.FALSE_POSITIVE
    assert {item["id"] for item in platform.fetch_open()} == {"a2"}
    platform.set_status("a2", TriageStatus.CLOSED, reason=CloseReason.TRUE_POSITIVE)
    assert platform.fetch_open() == []


def test_case_status_lifecycle():
    platform = InMemoryTriagePlatform([{"id": "a1"}])
    assert platform.case_status_of("a1") is None  # no case yet
    platform.create_case("a1", _investigation("a1"))
    assert platform.case_status_of("a1") == CaseStatus.OPEN
    platform.set_case_status("a1", CaseStatus.IN_PROGRESS)
    assert platform.case_status_of("a1") == CaseStatus.IN_PROGRESS
    platform.set_case_status("a1", CaseStatus.CLOSED)
    assert platform.case_status_of("a1") == CaseStatus.CLOSED


def test_set_case_status_is_noop_without_a_case():
    platform = InMemoryTriagePlatform([{"id": "a1"}])
    platform.set_case_status("a1", CaseStatus.CLOSED)  # no case created
    assert platform.case_status_of("a1") is None


def test_fetch_open_respects_limit():
    platform = InMemoryTriagePlatform([{"id": f"a{i}"} for i in range(5)])
    assert len(platform.fetch_open(limit=2)) == 2


def test_health_check_reports_open_count():
    platform = InMemoryTriagePlatform([{"id": "a1"}, {"id": "a2"}])
    status = platform.health_check()
    assert status["ok"] is True
    assert status["open_alerts"] == 2
