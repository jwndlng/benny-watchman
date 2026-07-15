"""Unit tests for ElasticSecurityPlatform (Kibana API, mocked HTTP)."""

from datetime import datetime, timezone

import pytest

from src.platforms.base import TriagePlatform, TriageStatus
from src.platforms.elastic import ElasticSecurityPlatform
from src.schemas.investigation import Investigation, InvestigationStatus


class _Resp:
    def __init__(self, payload: object) -> None:
        self._payload = payload

    def json(self) -> object:
        return self._payload

    def raise_for_status(self) -> None:
        return None


class _FakeKibana:
    """Records requests and returns canned responses keyed by (method, path)."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict]] = []

    def post(self, path: str, json: dict) -> _Resp:
        self.calls.append(("POST", path, json))
        if path == "/api/detection_engine/signals/search":
            return _Resp(
                {
                    "hits": {
                        "hits": [
                            {
                                "_id": "alert-1",
                                "_index": ".alerts-security.alerts-default",
                                "_source": {
                                    "@timestamp": "2026-03-13T10:00:00Z",
                                    "kibana.alert.rule.name": "brute-force",
                                    "kibana.alert.rule.uuid": "rule-123",
                                    "kibana.alert.reason": "many failed logins",
                                    "kibana.alert.severity": "high",
                                },
                            }
                        ]
                    }
                }
            )
        if path == "/api/cases":
            return _Resp({"id": "case-1", "version": "v1"})
        return _Resp({})  # comments, status, attach

    def patch(self, path: str, json: dict) -> _Resp:
        self.calls.append(("PATCH", path, json))
        return _Resp([{"id": "case-1", "version": "v2"}])

    def paths(self) -> list[str]:
        return [f"{m} {p}" for m, p, _ in self.calls]


def _platform() -> tuple[ElasticSecurityPlatform, _FakeKibana]:
    fake = _FakeKibana()
    return ElasticSecurityPlatform("https://kibana", "key", client=fake), fake


def _investigation() -> Investigation:
    now = datetime.now(timezone.utc)
    return Investigation(
        id="inv-1",
        alert_id="alert-1",
        status=InvestigationStatus.COMPLETE,
        report={"summary": "looks malicious"},
        created_at=now,
        completed_at=now,
    )


def test_satisfies_the_protocol():
    platform, _ = _platform()
    assert isinstance(platform, TriagePlatform)


def test_fetch_open_filters_and_maps_to_alert():
    platform, fake = _platform()
    items = platform.fetch_open()

    # request filtered on open workflow status
    _, _, body = fake.calls[0]
    assert body["query"]["bool"]["filter"] == [
        {"term": {"kibana.alert.workflow_status": "open"}}
    ]
    # mapped to a valid Alert-shaped dict
    assert len(items) == 1
    item = items[0]
    assert item["id"] == "alert-1"
    assert item["type"] == "brute-force"  # rule name drives runbook matching
    assert item["source"] == "elastic"


def test_mapped_item_validates_as_alert():
    from src.modules.siem.alert import Alert

    platform, _ = _platform()
    item = platform.fetch_open()[0]
    alert = Alert(**item)
    assert alert.type == "brute-force"


def test_set_status_maps_to_workflow_status():
    platform, fake = _platform()
    platform.set_status("alert-1", TriageStatus.CLOSED)
    platform.set_status("alert-1", TriageStatus.ESCALATED)
    statuses = [
        c[2]["status"]
        for c in fake.calls
        if c[1] == "/api/detection_engine/signals/status"
    ]
    assert statuses == ["closed", "acknowledged"]


def test_write_back_creates_case_comments_and_sets_case_severity():
    platform, fake = _platform()
    platform.fetch_open()  # populates the alert's index for attachment
    case_id = platform.create_case("alert-1", _investigation())
    assert case_id == "case-1"

    platform.comment("alert-1", "Benny triage — true_positive")
    platform.set_severity("alert-1", "high")

    paths = fake.paths()
    assert "POST /api/cases" in paths
    assert "POST /api/cases/case-1/comments" in paths
    assert "PATCH /api/cases" in paths
    # severity set on the case, normalized
    patch_body = next(c[2] for c in fake.calls if c[0] == "PATCH")
    assert patch_body["cases"][0]["severity"] == "high"


def test_comment_without_case_raises():
    platform, _ = _platform()
    with pytest.raises(ValueError):
        platform.comment("alert-1", "no case yet")


def test_platform_selection_by_config():
    from types import SimpleNamespace

    from src.api.app import _select_triage_platform
    from src.platforms.memory import InMemoryTriagePlatform

    configured = SimpleNamespace(
        kibana=SimpleNamespace(
            url="https://kibana", api_key="key", case_owner="securitySolution"
        )
    )
    assert isinstance(_select_triage_platform(configured), ElasticSecurityPlatform)

    unconfigured = SimpleNamespace(kibana=None)
    assert isinstance(_select_triage_platform(unconfigured), InMemoryTriagePlatform)
