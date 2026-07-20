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

from src.adapters.platforms.base import CaseStatus, CloseReason, TriageStatus

if TYPE_CHECKING:
    from src.schemas.investigation import Investigation

_SIGNALS_SEARCH = "/api/detection_engine/signals/search"
_SIGNALS_STATUS = "/api/detection_engine/signals/status"
_CASES = "/api/cases"

# TriageStatus → Elastic workflow status
_STATUS_MAP = {
    TriageStatus.CLOSED: "closed",
    TriageStatus.ACKNOWLEDGED: "acknowledged",
    TriageStatus.OPEN: "open",
}
_CASE_SEVERITIES = {"low", "medium", "high", "critical"}

# Human-readable labels for the close reason recorded on the case (the signals
# status API has no portable close-reason field — see the change's design spike).
_CLOSE_REASON_LABELS = {
    CloseReason.DUPLICATE: "Duplicate",
    CloseReason.FALSE_POSITIVE: "False positive",
    CloseReason.BENIGN_POSITIVE: "Benign positive",
    CloseReason.TRUE_POSITIVE: "True positive",
    CloseReason.OTHER: "Other",
}


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
        self._rule_note: dict[str, str | None] = {}  # rule uuid -> investigation note

    # --- intake / tracking ---

    def fetch_open(self, limit: int = 50) -> list[dict]:
        """Return open detection alerts, most recent first, capped at `limit`."""
        body = {
            "query": {"bool": {"filter": [{"term": {"kibana.alert.workflow_status": "open"}}]}},
            "sort": [{"@timestamp": "desc"}],
            "size": limit,
        }
        resp = self._client.post(_SIGNALS_SEARCH, json=body)
        resp.raise_for_status()
        hits = resp.json().get("hits", {}).get("hits", [])
        return [self._to_alert(hit) for hit in hits]

    def get(self, item_id: str) -> dict | None:
        """Return a single alert document by id, or None."""
        body = {"query": {"ids": {"values": [item_id]}}, "size": 1}
        resp = self._client.post(_SIGNALS_SEARCH, json=body)
        resp.raise_for_status()
        hits = resp.json().get("hits", {}).get("hits", [])
        return self._to_alert(hits[0]) if hits else None

    def acknowledge(self, item_id: str) -> None:
        """Claim the alert: set its Elastic workflow status to `acknowledged`."""
        self.set_status(item_id, TriageStatus.ACKNOWLEDGED)

    def set_status(self, item_id: str, status: TriageStatus, reason: CloseReason | None = None) -> None:
        """Drive the alert's Elastic workflow status (closed/acknowledged/open).

        On a `CLOSED` status with a reason, the human-readable reason is recorded
        on the alert's case when one exists — the signals status API has no portable
        close-reason field (see the change's design spike). A dedup close has no
        case, so its reason lives only in the triage log.
        """
        resp = self._client.post(
            _SIGNALS_STATUS,
            json={"signal_ids": [item_id], "status": _STATUS_MAP[status]},
        )
        resp.raise_for_status()
        if status == TriageStatus.CLOSED and reason not in (None, CloseReason.NONE):
            self._record_close_reason(item_id, reason)

    def _record_close_reason(self, item_id: str, reason: CloseReason) -> None:
        """Post the close reason as a case comment; no-op when the item has no case."""
        if item_id not in self._case:
            logfire.info(
                "elastic: no case for close reason, recording in log only", item_id=item_id, reason=reason.value
            )
            return
        label = _CLOSE_REASON_LABELS.get(reason, reason.value)
        self.comment(item_id, f"Benny closed this alert — reason: {label}.")

    # --- write-back (cases) ---

    def create_case(self, item_id: str, investigation: Investigation) -> str:
        """Open a Kibana case for the alert, attach it, and return the case id."""
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
        """Add a comment to the alert's case, refreshing the cached version."""
        case_id, version = self._require_case(item_id)
        resp = self._client.post(
            f"{_CASES}/{case_id}/comments",
            json={"type": "user", "comment": text, "owner": self._owner},
        )
        resp.raise_for_status()
        # Adding a comment bumps the case version; refresh it so a subsequent
        # PATCH (set_severity) doesn't 409 on a stale version.
        updated = resp.json()
        new_version = updated.get("version") if isinstance(updated, dict) else None
        self._case[item_id] = (case_id, new_version or version)

    def set_severity(self, item_id: str, severity: str) -> None:
        """Set the alert's case severity (no-op if already at target)."""
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
        # 406 = Kibana rejects a no-op update (severity already at target) — benign.
        if resp.status_code == 406:
            logfire.info("elastic: case severity already at target, skipping", item_id=item_id)
            return
        resp.raise_for_status()
        updated = resp.json()
        if isinstance(updated, list) and updated:
            self._case[item_id] = (case_id, updated[0].get("version", version))

    def set_case_status(self, item_id: str, status: CaseStatus) -> None:
        """Move the alert's Kibana case to a new status; no-op if it has no case."""
        if item_id not in self._case:
            logfire.info("elastic: no case to move, skipping", item_id=item_id, status=status.value)
            return
        case_id, version = self._case[item_id]
        resp = self._client.patch(
            _CASES,
            json={"cases": [{"id": case_id, "version": version, "status": status.value}]},
        )
        # 406 = Kibana rejects a no-op update (already at that status) — benign.
        if resp.status_code == 406:
            logfire.info("elastic: case already at status, skipping", item_id=item_id, status=status.value)
            return
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
                    "query": {"bool": {"filter": [{"term": {"kibana.alert.workflow_status": "open"}}]}},
                    "size": 0,
                },
            )
            resp.raise_for_status()
            total = resp.json().get("hits", {}).get("total", 0)
            open_alerts = total.get("value") if isinstance(total, dict) else total
            checks["alerts_read"] = "ok"
        except Exception as exc:
            checks["alerts_read"] = f"error: {exc}"
        try:
            resp = self._client.get(f"{_CASES}/_find", params={"owner": self._owner, "perPage": 1})
            resp.raise_for_status()
            checks["cases_access"] = "ok"
        except Exception as exc:
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
            raise ValueError(f"no case for item {item_id}; call create_case before comment/set_severity")
        return self._case[item_id]

    def _attach_alert(self, case_id: str, item_id: str) -> None:
        """Best-effort RAC alert attachment; skipped if the source index is unknown."""
        index = self._index.get(item_id)
        if not index:
            logfire.info("elastic: no index for alert, skipping attach", item_id=item_id)
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
        except httpx.HTTPError as exc:
            logfire.warn("elastic: alert attach failed", item_id=item_id, error=str(exc))
            return
        # Attaching an alert bumps the case version — refresh it so the next PATCH
        # (e.g. set_case_status) doesn't 409 on a stale version.
        updated = resp.json()
        new_version = updated.get("version") if isinstance(updated, dict) else None
        if new_version:
            self._case[item_id] = (case_id, new_version)

    def _to_alert(self, hit: dict) -> dict:
        src = hit.get("_source", {})
        rule_name = _dig(src, "kibana.alert.rule.name")
        rule_uuid = _dig(src, "kibana.alert.rule.uuid")
        # remember for write-back
        item_id = hit.get("_id", "")
        self._index[item_id] = hit.get("_index", "")
        self._rule[item_id] = {"id": rule_uuid, "name": rule_name}
        return {
            "id": item_id,
            "type": rule_name or "unknown",
            "title": rule_name or "Elastic alert",
            "description": _dig(src, "kibana.alert.reason") or "",
            "severity": (_dig(src, "kibana.alert.severity") or "low"),
            "source": "elastic",
            "timestamp": src.get("@timestamp"),
            "raw": src,
            "guidance": self._guidance(src, rule_uuid),
        }

    def _guidance(self, src: dict, rule_uuid: str | None) -> dict | None:
        """Build investigation guidance from the detection rule's note.

        Reads the note from the alert document's rule parameters and caches it per
        rule uuid so cost is per-unique-rule, not per-alert. Returns None when the
        rule has no note. (The live rule-API fallback is deferred — see the change's
        open question on the exact note field path.)
        """
        if rule_uuid is not None and rule_uuid in self._rule_note:
            note = self._rule_note[rule_uuid]
        else:
            note = _dig(src, "kibana.alert.rule.parameters.note")
            if rule_uuid is not None:
                self._rule_note[rule_uuid] = note
        if not note:
            return None
        return {
            "text": note,
            "source": "elastic-rule-note",
            "author": _dig(src, "kibana.alert.rule.created_by"),
        }
