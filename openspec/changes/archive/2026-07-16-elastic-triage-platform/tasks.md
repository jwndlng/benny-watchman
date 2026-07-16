## 1. Spike — confirm Elastic APIs (do first)

- [ ] 1.1 Against DFINITY's Elastic/Kibana: confirm the detection **alerts index** pattern and the "needs triage" filter (`kibana.alert.workflow_status: open`)
- [ ] 1.2 Confirm the **signals status API** shape (`POST /api/detection_engine/signals/status`, `{signal_ids, status}`) and the valid statuses (`open`/`acknowledged`/`closed`)
- [ ] 1.3 Confirm the **Cases API**: create (`POST /api/cases`, owner `securitySolution`), attach alert (`/comments` with `type: alert`), add comment, set case severity
- [ ] 1.4 Confirm whether **alert severity** is settable (expected: no → use case severity) and the `Alert.type` source (rule name vs a curated tag/rule-id map)
- [ ] 1.5 Confirm **auth**: Kibana API key vs ES API key (one credential or two), and space/namespace
- [ ] 1.6 Record findings; adjust the design's endpoint/field assumptions if they differ

## 2. Config & selection

- [x] 2.1 Add Elastic-triage settings to `config.py` (Kibana URL, API key, alerts index, case owner/space); optional, auto-off when unset
- [x] 2.2 `create_app`: build `ElasticSecurityPlatform` when configured, else `InMemoryTriagePlatform`

## 3. ElasticSecurityPlatform — reads (Kibana API)

- [x] 3.1 `src/platforms/elastic.py` — `ElasticSecurityPlatform` implementing `TriagePlatform` over a single **injectable Kibana HTTP client** (httpx, `Authorization: ApiKey` + `kbn-xsrf`); no Elasticsearch client
- [x] 3.2 `fetch_open(limit)` — `POST /api/detection_engine/signals/search` filtered to `workflow_status: open`, newest first, as raw dicts each with an `id`
- [x] 3.3 `get(item_id)` — signals search by `_id`

## 4. ElasticSecurityPlatform — writes (Kibana API)

- [x] 4.1 Reuse the same Kibana client for writes
- [x] 4.2 `create_case(item_id, investigation)` — create case, attach the alert, return + retain `item_id → case_id`
- [x] 4.3 `comment(item_id, text)` — post a comment to the item's case
- [x] 4.4 `set_severity(item_id, severity)` — set the **case** severity (normalize `outcome.priority` → `low|medium|high|critical`)
- [x] 4.5 `set_status(item_id, status)` — signals status API: `CLOSED`→`closed`, `ESCALATED`→`acknowledged`

## 5. Alert mapping

- [x] 5.1 Map an Elastic alert document → SIEM `Alert` (per the design table); `type` drives runbook matching

## 6. Tests & verify

- [x] 6.1 Mock the Elastic/Kibana HTTP layer; test `fetch_open` returns only open alerts as `id`-bearing dicts
- [x] 6.2 Test the alert→`Alert` mapping produces a valid `Alert` with the expected `type`
- [x] 6.3 Test write-back calls: `create_case` (create + attach + retained id), `comment`, `set_severity` (case severity), `set_status` (`closed`/`acknowledged`)
- [x] 6.4 Test config selection: Elastic when configured, in-memory fallback otherwise (no Elastic calls)
- [x] 6.5 `make test` green, `make lint` clean
- [x] 6.6 Update `AGENT.md` / `README.md` — note the Elastic platform + required key scopes

## 7. Ship

- [ ] 7.1 In a configured environment, point `run_once` at `ElasticSecurityPlatform` and dry-run against a small alert set
- [ ] 7.2 Deferred: scheduling/daemonizing the loop for 24/7 operation
