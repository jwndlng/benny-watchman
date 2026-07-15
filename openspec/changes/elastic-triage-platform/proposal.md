## Why

`triage-platform` shipped the `TriagePlatform` abstraction, the triage-loop, and an in-memory reference implementation — the whole loop is proven end-to-end, but against a fake platform. This change delivers the **first real implementation**: `ElasticSecurityPlatform`, so Benny can triage live alerts in DFINITY's Elastic SIEM. This is the last mile to production value: point `run_once` at Elastic instead of the in-memory platform and Benny starts clearing the noise floor with a full audit trail.

## What Changes

- **`ElasticSecurityPlatform`** — a concrete `TriagePlatform` (under `src/platforms/`) backed by Elastic Security:
  - `fetch_open()` — query the Elastic **alerts index** (e.g. `.alerts-security.alerts-*`) for alerts still needing triage (open workflow status, not yet handled by Benny), returned as raw dicts.
  - `get(id)` — fetch a single alert document by id.
  - `create_case(id, investigation)` — open a **Kibana Case** (Cases API) linked to the alert; return the case id.
  - `comment(id, text)` — attach Benny's reasoning as a case/alert comment.
  - `set_severity(id, severity)` — set the assessed severity (target TBD by the spike — case severity vs alert vs workflow tag).
  - `set_status(id, status)` — drive the alert's workflow status (open → acknowledged/closed) so triaged alerts drop out of `fetch_open`; `ESCALATED` leaves it open (+ tag), `CLOSED` closes it.
- **Alert → `Alert` mapping** — translate an Elastic alert document into the SIEM module's `Alert` schema (notably which field becomes `type` for runbook matching, e.g. `kibana.alert.rule.name`/tags).
- **Wiring** — select the platform implementation by config (in-memory for dev, Elastic when configured); `run_once(orchestrator, ElasticSecurityPlatform, hint="siem")`.
- **Read vs write surfaces** — reads use the Elasticsearch client (alerts index); writes use the Kibana Cases + detection-engine (signals) APIs. Both behind the one `ElasticSecurityPlatform`.

## Capabilities

### New Capabilities
- `elastic-triage-platform`: an `ElasticSecurityPlatform` implementation of `TriagePlatform` (fetch open alerts + write back comments, cases, severity, status), plus the Elastic-alert→`Alert` mapping and config-driven platform selection

### Modified Capabilities
- None to the `TriagePlatform` contract — this implements the existing interface unchanged. (Config gains Elastic-triage settings.)

### Non-Goals
- Changing the `TriagePlatform` interface or the triage-loop (both from `triage-platform`)
- Scheduling/daemonizing the loop for 24/7 operation (deployment)
- Remediation (block/isolate/disable) — writes are scoped to triage metadata + cases
- Other SIEM backends (Splunk, Sentinel, …) and the VM platform

## Impact

- **Depends on:** `triage-platform` merged (the `TriagePlatform` Protocol, `run_once`, `TriageStatus`)
- `src/platforms/elastic.py` — `ElasticSecurityPlatform`; reuses the existing `ElasticsearchEngine`/client for reads, a Kibana API client (httpx) for writes
- `src/config.py` — Elastic-triage settings (alerts index, Kibana URL, API key, case connector); platform selection (in-memory vs Elastic)
- `src/api/app.py` — build the Elastic platform when configured, else in-memory
- Tests — mock the Elastic/Kibana HTTP layer; assert the mapping and each write-back call; the loop itself is already covered by `triage-platform`
- **Permission boundary:** the Elastic API key is scoped to **alerts read + cases write + signal status write** — never remediation. Documented and enforced at the key.

### Open questions — resolved by Task 1 (the spike)
- **`set_severity` semantics:** can an alert's severity be set, or does it map to the **case** severity / a workflow tag? (Alert severity is rule-derived; likely case-level.)
- **Alerts index & query:** exact index pattern and the "needs triage" filter (`kibana.alert.workflow_status: open` + a "not seen by Benny" marker/tag).
- **Comment/case targeting:** does `comment` land on the alert or the case? (Likely the case.)
- **Field mapping:** which Elastic alert field drives `Alert.type` for runbook matching.
- **Auth/tenancy:** Kibana API key vs ES API key; space/namespace handling.
