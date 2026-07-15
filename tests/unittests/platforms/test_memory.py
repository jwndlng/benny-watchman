"""Unit tests for InMemoryTriagePlatform."""

from src.platforms.base import TriagePlatform, TriageStatus
from src.platforms.memory import InMemoryTriagePlatform


def test_satisfies_the_protocol():
    assert isinstance(InMemoryTriagePlatform([]), TriagePlatform)


def test_fetch_open_returns_open_items_with_ids():
    platform = InMemoryTriagePlatform([{"id": "a1"}, {"id": "a2"}])
    ids = {item["id"] for item in platform.fetch_open()}
    assert ids == {"a1", "a2"}


def test_terminal_status_drops_item_from_open_queue():
    platform = InMemoryTriagePlatform([{"id": "a1"}, {"id": "a2"}])
    platform.set_status("a1", TriageStatus.CLOSED)
    assert {item["id"] for item in platform.fetch_open()} == {"a2"}
    platform.set_status("a2", TriageStatus.ESCALATED)
    assert platform.fetch_open() == []


def test_fetch_open_respects_limit():
    platform = InMemoryTriagePlatform([{"id": f"a{i}"} for i in range(5)])
    assert len(platform.fetch_open(limit=2)) == 2
