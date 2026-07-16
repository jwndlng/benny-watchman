"""ElasticSecurityPlatform — a TriagePlatform backed by the Kibana Security app.

All operations go through the Kibana API (detection-engine signals search +
status, and Cases) over one injectable HTTP client. This platform never touches
the Elasticsearch client — that is the DataAgent's (evidence) surface.

Endpoint shapes follow standard Elastic Security 8.x APIs; confirm against the
target cluster (the change's spike) before relying on them in production.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import httpx
import logfire

from src.platforms.base import TriageStatus

if TYPE_CHECKING:
    from src.schemas.investigation import Investigation

_SIGNALS_SEARCH = "/api/detection_engine/signals/search"
_SIGNALS_STATUS = "/api/detection_engine/signals/status"
_CASES = "/api/cases"

# TriageStatus → Elastic workflow status
_STATUS_MAP = {
    TriageStatus.CLOSED: "closed",
    TriageStatus.ESCALATED: "acknowledged",
    TriageStatus.OPEN: "open",
}
_CASE_SEVERITIES = {"low", "medium", "high", "critical"}


def _dig(src: dict, dotted: str) -> Any:
    """Read a field that may be stored flat ('a.b.c') or nested ({'a':{'b':{'c'}}})."""
    if dotted in src:
        return src[dotted]
    cur: Any = src
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def _norm_severity(priority: str) -> str:
    """Normalize an outcome priority to an Elastic case severity."""
    p = (priority or "").lower()
    return p if p in _CASE_SEVERITIES else "low"


class ElasticSecurityPlatform:
    """TriagePlatform over the Kibana Security app API."""

    def __init__(
        self,
        kibana_url: str,
        api_key: str,
        case_owner: str = "securitySolution",
        client: httpx.Client | None = None,
    ) -> None:
        self._owner = case_owner
        self._client = client or httpx.Client(
            base_url=kibana_url.rstrip("/"),
            headers={
                "Authorization": f"ApiKey {api_key}",
                "kbn-xsrf": "true",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
        # Per-run state so write-back can resolve the alert's case + source index.
        self._case: dict[str, tuple[str, str]] = {}  # item_id -> (case_id, version)
        self._index: dict[str, str] = {}  # item_id -> alert source index
        self._rule: dict[str, dict] = {}  # item_id -> {"id","name"}

    # --- intake / tracking ---

    def fetch_open(self, limit: int = 50) -> list[dict]:
        body = {
            "query": {
                "bool": {"filter": [{"term": {"kibana.alert.workflow_status": "open"}}]}
            },
            "sort": [{"@timestamp": "desc"}],
            "size": limit,
        }
        resp = self._client.post(_SIGNALS_SEARCH, json=body)
        resp.raise_for_status()
        hits = resp.json().get("hits", {}).get("hits", [])
        return [self._to_alert(hit) for hit in hits]

    def get(self, item_id: str) -> dict | None:
        body = {"query": {"ids": {"values": [item_id]}}, "size": 1}
        resp = self._client.post(_SIGNALS_SEARCH, json=body)
        resp.raise_for_status()
        hits = resp.json().get("hits", {}).get("hits", [])
        return self._to_alert(hits[0]) if hits else None

    def set_status(self, item_id: str, status: TriageStatus) -> None:
        resp = self._client.post(
            _SIGNALS_STATUS,
            json={"signal_ids": [item_id], "status": _STATUS_MAP[status]},
        )
        resp.raise_for_status()

    # --- write-back (cases) ---

    def create_case(self, item_id: str, investigation: Investigation) -> str:
        title = f"[Benny] {item_id}"
        summary = (investigation.report or {}).get("summary", "")
        resp = self._client.post(
            _CASES,
            json={
                "title": title,
                "description": f"Automated triage by Benny for alert {item_id}.\n\n{summary}",
                "tags": ["benny"],
                "connector": {
                    "id": "none",
                    "name": "none",
                    "type": ".none",
                    "fields": None,
                },
                "settings": {"syncAlerts": False},
                "owner": self._owner,
            },
        )
        resp.raise_for_status()
        case = resp.json()
        case_id = case["id"]
        self._case[item_id] = (case_id, case.get("version", ""))
        self._attach_alert(case_id, item_id)
        return case_id

    def comment(self, item_id: str, text: str) -> None:
        case_id, _ = self._require_case(item_id)
        resp = self._client.post(
            f"{_CASES}/{case_id}/comments",
            json={"type": "user", "comment": text, "owner": self._owner},
        )
        resp.raise_for_status()

    def set_severity(self, item_id: str, severity: str) -> None:
        case_id, version = self._require_case(item_id)
        resp = self._client.patch(
            _CASES,
            json={
                "cases": [
                    {
                        "id": case_id,
                        "version": version,
                        "severity": _norm_severity(severity),
                    }
                ]
            },
        )
        resp.raise_for_status()
        updated = resp.json()
        if isinstance(updated, list) and updated:
            self._case[item_id] = (case_id, updated[0].get("version", version))

    def health_check(self) -> dict:
        """Read-only probe of alerts + cases access; no triage, no mutation."""
        checks: dict[str, str] = {}
        open_alerts: int | None = None
        try:
            resp = self._client.post(
                _SIGNALS_SEARCH,
                json={
                    "query": {
                        "bool": {
                            "filter": [
                                {"term": {"kibana.alert.workflow_status": "open"}}
                            ]
                        }
                    },
                    "size": 0,
                },
            )
            resp.raise_for_status()
            total = resp.json().get("hits", {}).get("total", 0)
            open_alerts = total.get("value") if isinstance(total, dict) else total
            checks["alerts_read"] = "ok"
        except Exception as exc:  # noqa: BLE001
            checks["alerts_read"] = f"error: {exc}"
        try:
            resp = self._client.get(
                f"{_CASES}/_find", params={"owner": self._owner, "perPage": 1}
            )
            resp.raise_for_status()
            checks["cases_access"] = "ok"
        except Exception as exc:  # noqa: BLE001
            checks["cases_access"] = f"error: {exc}"
        return {
            "platform": "elastic",
            "ok": all(v == "ok" for v in checks.values()),
            "checks": checks,
            "open_alerts": open_alerts,
        }

    # --- helpers ---

    def _require_case(self, item_id: str) -> tuple[str, str]:
        if item_id not in self._case:
            raise ValueError(
                f"no case for item {item_id}; call create_case before comment/set_severity"
            )
        return self._case[item_id]

    def _attach_alert(self, case_id: str, item_id: str) -> None:
        """Best-effort RAC alert attachment; skipped if the source index is unknown."""
        index = self._index.get(item_id)
        if not index:
            logfire.info(
                "elastic: no index for alert, skipping attach", item_id=item_id
            )
            return
        try:
            resp = self._client.post(
                f"{_CASES}/{case_id}/comments",
                json={
                    "type": "alert",
                    "alertId": [item_id],
                    "index": [index],
                    "rule": self._rule.get(item_id, {"id": None, "name": None}),
                    "owner": self._owner,
                },
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:  # noqa: BLE001
            logfire.warn(
                "elastic: alert attach failed", item_id=item_id, error=str(exc)
            )

    def _to_alert(self, hit: dict) -> dict:
        src = hit.get("_source", {})
        rule_name = _dig(src, "kibana.alert.rule.name")
        # remember for write-back
        item_id = hit.get("_id", "")
        self._index[item_id] = hit.get("_index", "")
        self._rule[item_id] = {
            "id": _dig(src, "kibana.alert.rule.uuid"),
            "name": rule_name,
        }
        return {
            "id": item_id,
            "type": rule_name or "unknown",
            "title": rule_name or "Elastic alert",
            "description": _dig(src, "kibana.alert.reason") or "",
            "severity": (_dig(src, "kibana.alert.severity") or "low"),
            "source": "elastic",
            "timestamp": src.get("@timestamp"),
            "raw": src,
        }
