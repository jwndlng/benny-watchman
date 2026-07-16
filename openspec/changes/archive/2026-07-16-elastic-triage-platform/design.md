# Design: ElasticSecurityPlatform

## Context

`triage-platform` shipped the `TriagePlatform` Protocol + triage-loop + in-memory impl. This change implements the first real platform against Elastic Security so Benny triages live DFINITY alerts. The interface is fixed; the work is mapping its six operations onto the **Kibana security-app APIs**: detection-engine signals search (read alerts), signals status (workflow), and Cases (write-back).

**Boundary:** `DataAgent` talks to the **Elasticsearch API** (evidence/data queries); `TriagePlatform` talks to the **Kibana API** (the operational security app). The two integrations never share a client — a clean separation.

The Elastic specifics below are **decisions based on standard Elastic Security 8.x APIs**, to be confirmed against the real instance in Task 1 (the spike) — they are the design's best-guess, not verified against DFINITY's cluster.

## Goals / Non-Goals

**Goals:**
- `ElasticSecurityPlatform` implementing every `TriagePlatform` method against Elastic
- Elastic alert document → SIEM `Alert` mapping (drives runbook matching)
- Config-driven platform selection (in-memory dev / Elastic when configured)
- HTTP layer mockable so tests assert mapping + each write-back call

**Non-Goals:**
- Changing the `TriagePlatform` interface or triage-loop
- Scheduling the loop (deployment), remediation, other SIEMs

## Decisions

### D1. Reads — via the Kibana detection-engine API
`fetch_open()` fetches alerts through the **Kibana** detection-engine signals search API (`POST /api/detection_engine/signals/search`, an ES query-DSL body) filtered to `kibana.alert.workflow_status: open`, newest first, `limit`-bounded. `get(id)` searches by `_id`. Work items are raw dicts (the loop/module validate). The platform does **not** touch the Elasticsearch client — reads and writes are all Kibana.

### D2. Tracking = workflow status (not a Benny cursor)
`set_status` maps to the **detection-engine signals status API** (`POST /api/detection_engine/signals/status`, `{signal_ids, status}`):
- `TriageStatus.CLOSED` → Elastic `closed` (benign/false-positive)
- `TriageStatus.ESCALATED` → Elastic `acknowledged` (Benny handled it; the *case* is what a human works)

`fetch_open` filters on `workflow_status: open`, so both terminal states drop the alert out of the queue — Benny stays stateless, state lives in Elastic.

### D3. Write-back — Kibana Cases API
- `create_case(item_id, investigation)` → `POST /api/cases` (owner `securitySolution`), attaches the alert (`POST /api/cases/{id}/comments` with `type: alert`), returns the case id.
- `comment(item_id, text)` → a user comment on that case.
- `set_severity(item_id, severity)` → the **case** severity (`low|medium|high|critical`). **Alert severity is rule-derived and not settable**, so severity maps to the case; `outcome.priority` is normalized to Elastic's scale.
- The platform keeps an in-run `item_id → case_id` map (populated by `create_case`, which the loop calls first), so `comment`/`set_severity` resolve the case. Cross-run persistence isn't needed: idempotency (dedup) + the `workflow_status: open` filter prevent re-processing.

### D4. Alert → `Alert` mapping
| `Alert` field | Elastic source |
|---|---|
| `id` | `_id` |
| `type` | `kibana.alert.rule.name` (assumption — the runbook-matching key; may become a tag/rule-id mapping) |
| `title` | `kibana.alert.rule.name` |
| `description` | `kibana.alert.reason` |
| `severity` | `kibana.alert.severity` |
| `source` | `"elastic"` |
| `timestamp` | `@timestamp` |
| `raw` | the full alert document |

### D5. One Kibana client (the DataAgent/Platform split)
A single Kibana HTTP client (httpx; `Authorization: ApiKey <key>` + `kbn-xsrf` header on writes) serves **every** operation — alerts search, signals status, cases. `ElasticSecurityPlatform` does **not** use the Elasticsearch client: that is `DataAgent`'s surface (evidence queries). Clean separation — **DataAgent ↔ Elasticsearch API, TriagePlatform ↔ Kibana API** — so the two integrations never overlap. The client is injectable so tests mock the HTTP layer.

### D6. Config & selection
New settings (optional, auto-off when unset): Kibana base URL, API key, alerts index pattern, case owner/space. `create_app` builds `ElasticSecurityPlatform` when configured, else `InMemoryTriagePlatform`. Reuse the existing `ELASTIC_HOST`/`ELASTIC_API_KEY` where they apply; add `KIBANA_URL` etc. for the write APIs.

### D7. Permission boundary
The API key is scoped to **alerts read + signal-status write + cases all** — never remediation. The platform exposes no destructive action.

## Risks / Trade-offs

- **API drift by Elastic version** → paths/fields differ across 8.x; Task 1 confirms against the real cluster; keep endpoints/fields in one place for easy adjustment.
- **`set_severity` is case-level, not alert-level** → accepted (alert severity is rule-owned); documented so operators aren't surprised.
- **Case-always volume** → one case per alert (incl. auto-closed benign) can flood the case list at scale. It's the deliberate traceability decision; a severity/disposition threshold can be added later if noise warrants. Flagged, not changed.
- **Write-back partial failure** (case created, comment fails) → best-effort with logging for MVP; revisit atomicity if needed.

## Migration Plan

1. **Spike (Task 1):** confirm against DFINITY Elastic — alerts index name + open filter, signals status API shape, Cases API + alert attachment, whether alert severity is truly unsettable, API-key auth/space.
2. Implement reads (`fetch_open`/`get`) with the ES client.
3. Implement writes (`create_case`/`comment`/`set_severity`/`set_status`) with the Kibana client.
4. Alert→`Alert` mapping.
5. Config + `create_app` selection (in-memory ↔ Elastic).
6. Tests (mock HTTP): mapping, each write-back call, status→queue behavior.
7. Point `run_once` at the Elastic platform in a configured environment.

## Open Questions

- Confirm the alerts index pattern and space/namespace in DFINITY's cluster.
- Kibana API key vs ES API key — one credential or two (ES read + Kibana write)?
- Exact `Alert.type` source for runbook matching (rule name vs a curated tag/rule-id map).
- Should escalation add a Benny **workflow tag** in addition to `acknowledged`, for human filtering?
