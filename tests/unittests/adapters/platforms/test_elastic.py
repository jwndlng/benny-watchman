"""Unit tests for ElasticSecurityPlatform (Kibana API, mocked HTTP)."""

from datetime import datetime, timezone

import pytest

from src.adapters.platforms.base import CaseStatus, CloseReason, TriagePlatform, TriageStatus
from src.adapters.platforms.elastic import ElasticSecurityPlatform
from src.schemas.investigation import Investigation, InvestigationStatus


class _Resp:
    def __init__(self, payload: object, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> object:
        return self._payload

    def raise_for_status(self) -> None:
        return None


class _FakeKibana:
    """Records requests and returns canned responses keyed by (method, path)."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict]] = []
        self.patched_version: str | None = None
        self.patch_status: int = 200

    def post(self, path: str, json: dict) -> _Resp:
        self.calls.append(("POST", path, json))
        if path == "/api/detection_engine/signals/search":
            return _Resp(
                {
                    "hits": {
                        "total": {"value": 1},
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
                        ],
                    }
                }
            )
        if path == "/api/cases":
            return _Resp({"id": "case-1", "version": "v-create"})
        if path.endswith("/comments"):
            # a comment bumps the case version (real Kibana behavior)
            return _Resp({"id": "case-1", "version": "v-comment"})
        return _Resp({})  # status, attach

    def patch(self, path: str, json: dict) -> _Resp:
        self.calls.append(("PATCH", path, json))
        self.patched_version = json["cases"][0].get("version")
        if self.patch_status == 406:
            return _Resp({"error": "no-op update"}, status_code=406)
        return _Resp([{"id": "case-1", "version": "v2"}])

    def get(self, path: str, params: dict | None = None) -> _Resp:
        self.calls.append(("GET", path, params or {}))
        return _Resp({"cases": [], "total": 0})

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
    assert callable(platform.acknowledge)
    assert callable(platform.set_case_status)


def test_fetch_open_filters_and_maps_to_alert():
    platform, fake = _platform()
    items = platform.fetch_open()

    # request filtered on open workflow status
    _, _, body = fake.calls[0]
    assert body["query"]["bool"]["filter"] == [{"term": {"kibana.alert.workflow_status": "open"}}]
    # mapped to a valid Alert-shaped dict
    assert len(items) == 1
    item = items[0]
    assert item["id"] == "alert-1"
    assert item["type"] == "brute-force"  # rule name is metadata, not a match key
    assert item["source"] == "elastic"


def test_mapped_item_validates_as_alert():
    from src.modules.siem.schemas.alert import Alert

    platform, _ = _platform()
    item = platform.fetch_open()[0]
    alert = Alert(**item)
    assert alert.type == "brute-force"


def test_rule_note_becomes_guidance():
    platform, _ = _platform()
    hit = {
        "_id": "a1",
        "_index": ".alerts-security.alerts-default",
        "_source": {
            "@timestamp": "2026-03-13T10:00:00Z",
            "kibana.alert.rule.name": "brute-force",
            "kibana.alert.rule.uuid": "rule-1",
            "kibana.alert.rule.parameters.note": "Check source IP reputation and recent auth history.",
            "kibana.alert.rule.created_by": "detection-eng",
        },
    }
    item = platform._to_alert(hit)
    assert item["guidance"]["text"].startswith("Check source IP reputation")
    assert item["guidance"]["source"] == "elastic-rule-note"
    assert item["guidance"]["author"] == "detection-eng"


def test_guidance_item_validates_as_alert():
    from src.modules.siem.schemas.alert import Alert

    platform, _ = _platform()
    hit = {
        "_id": "a1",
        "_index": ".alerts",
        "_source": {
            "@timestamp": "2026-03-13T10:00:00Z",
            "kibana.alert.rule.name": "brute-force",
            "kibana.alert.rule.uuid": "rule-1",
            "kibana.alert.rule.parameters.note": "Investigate lateral movement.",
        },
    }
    alert = Alert(**platform._to_alert(hit))
    assert alert.guidance is not None
    assert alert.guidance.source == "elastic-rule-note"


def test_no_rule_note_yields_no_guidance():
    platform, _ = _platform()
    item = platform.fetch_open()[0]  # canned hit carries no investigation note
    assert item["guidance"] is None


def test_rule_note_cached_per_rule():
    platform, _ = _platform()
    with_note = {
        "_id": "a1",
        "_index": ".alerts",
        "_source": {
            "kibana.alert.rule.uuid": "rule-1",
            "kibana.alert.rule.parameters.note": "Investigate lateral movement.",
        },
    }
    without_note = {  # same rule, note absent on this doc — must resolve from cache
        "_id": "a2",
        "_index": ".alerts",
        "_source": {"kibana.alert.rule.uuid": "rule-1"},
    }
    first = platform._to_alert(with_note)
    second = platform._to_alert(without_note)
    assert first["guidance"]["text"] == "Investigate lateral movement."
    assert second["guidance"]["text"] == "Investigate lateral movement."


def test_acknowledge_and_set_status_map_to_workflow_status():
    platform, fake = _platform()
    platform.acknowledge("alert-1")
    platform.set_status("alert-1", TriageStatus.CLOSED)
    statuses = [c[2]["status"] for c in fake.calls if c[1] == "/api/detection_engine/signals/status"]
    assert statuses == ["acknowledged", "closed"]


def test_close_with_reason_records_reason_on_case():
    platform, fake = _platform()
    platform.fetch_open()  # populates the alert index
    platform.create_case("alert-1", _investigation())
    platform.set_status("alert-1", TriageStatus.CLOSED, reason=CloseReason.TRUE_POSITIVE)

    # alert is closed
    statuses = [c[2]["status"] for c in fake.calls if c[1] == "/api/detection_engine/signals/status"]
    assert statuses == ["closed"]
    # the reason is recorded as a user comment on the case
    user_comments = [c[2]["comment"] for c in fake.calls if c[1].endswith("/comments") and "comment" in c[2]]
    assert any("True positive" in body for body in user_comments)


def test_close_with_reason_without_case_does_not_raise():
    platform, fake = _platform()
    # dedup path: no case created — must still close the alert, reason logged only
    platform.set_status("alert-1", TriageStatus.CLOSED, reason=CloseReason.DUPLICATE)
    statuses = [c[2]["status"] for c in fake.calls if c[1] == "/api/detection_engine/signals/status"]
    assert statuses == ["closed"]


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


def test_set_case_status_patches_case_status():
    platform, fake = _platform()
    platform.fetch_open()
    platform.create_case("alert-1", _investigation())
    platform.set_case_status("alert-1", CaseStatus.IN_PROGRESS)
    platform.set_case_status("alert-1", CaseStatus.CLOSED)
    statuses = [c[2]["cases"][0]["status"] for c in fake.calls if c[0] == "PATCH" and "status" in c[2]["cases"][0]]
    assert statuses == ["in-progress", "closed"]


def test_set_case_status_without_case_is_noop():
    platform, fake = _platform()
    platform.set_case_status("alert-1", CaseStatus.CLOSED)  # no case created
    assert all(c[0] != "PATCH" for c in fake.calls)


def test_set_case_status_uses_version_refreshed_after_attach():
    # regression: create_case attaches the alert (a comment that bumps the case
    # version); the following set_case_status PATCH must use the post-attach
    # version ("v-comment"), not the stale create-time version ("v-create"),
    # or Kibana 409s on /api/cases.
    platform, fake = _platform()
    platform.fetch_open()  # populates the alert index so the alert is attached
    platform.create_case("alert-1", _investigation())
    platform.set_case_status("alert-1", CaseStatus.IN_PROGRESS)
    assert fake.patched_version == "v-comment"


def test_set_severity_uses_version_refreshed_after_comment():
    # regression: comment() bumps the case version; set_severity must PATCH with the
    # refreshed version, not the stale create-time version (else Kibana 409s).
    platform, fake = _platform()
    platform.fetch_open()
    platform.create_case("alert-1", _investigation())  # version "v-create"
    platform.comment("alert-1", "benny note")  # bumps to "v-comment"
    platform.set_severity("alert-1", "high")
    assert fake.patched_version == "v-comment"


def test_set_severity_tolerates_noop_406():
    # a no-op severity PATCH (target == current) returns 406 in Kibana; benign.
    platform, fake = _platform()
    platform.fetch_open()
    platform.create_case("alert-1", _investigation())
    fake.patch_status = 406
    platform.set_severity("alert-1", "low")  # must not raise


def test_health_check_probes_alerts_and_cases_read_only():
    platform, fake = _platform()
    status = platform.health_check()

    assert status["platform"] == "elastic"
    assert status["ok"] is True
    assert status["checks"]["alerts_read"] == "ok"
    assert status["checks"]["cases_access"] == "ok"
    assert status["open_alerts"] == 1
    # read-only: no case created, no status change
    assert "POST /api/cases" not in fake.paths()
    assert all(c[1] != "/api/detection_engine/signals/status" for c in fake.calls)


def test_comment_without_case_raises():
    platform, _ = _platform()
    with pytest.raises(ValueError):
        platform.comment("alert-1", "no case yet")


def test_kibana_space_prefix_is_preserved_in_request_paths():
    # a /s/<space-id> prefix in the Kibana url must scope all API calls
    platform = ElasticSecurityPlatform("https://host/s/isec", "key")
    req = platform._client.build_request("POST", "/api/detection_engine/signals/search")
    assert str(req.url) == "https://host/s/isec/api/detection_engine/signals/search"


def test_no_space_prefix_uses_default_space():
    platform = ElasticSecurityPlatform("https://host", "key")
    req = platform._client.build_request("POST", "/api/cases")
    assert str(req.url) == "https://host/api/cases"


def test_platform_selection_by_config():
    from types import SimpleNamespace

    from src.adapters.api.app import _select_triage_platform
    from src.adapters.platforms.memory import InMemoryTriagePlatform

    configured = SimpleNamespace(
        kibana=SimpleNamespace(url="https://kibana", api_key="key", case_owner="securitySolution")
    )
    assert isinstance(_select_triage_platform(configured), ElasticSecurityPlatform)

    unconfigured = SimpleNamespace(kibana=None)
    assert isinstance(_select_triage_platform(unconfigured), InMemoryTriagePlatform)
