## 1. Baseline

- [ ] 1.1 Branch off `main`; confirm `make test` green
- [ ] 1.2 Create the `src/platforms/` package (`__init__.py`)

## 2. Abstraction

- [ ] 2.1 `src/platforms/base.py` — `TriageStatus` enum (`OPEN`, `ESCALATED`, `CLOSED`) and the `TriagePlatform` Protocol (`fetch_open`, `get`, `comment`, `set_severity`, `set_status`, `create_case`)
- [ ] 2.2 Confirm the Protocol imports only `core`/`schemas` types (no `modules`), keeping work items as raw dicts

## 3. In-memory reference implementation

- [ ] 3.1 `src/platforms/memory.py` — `InMemoryTriagePlatform`: seeded raw work items + per-item status; records comments, severities, and cases in memory
- [ ] 3.2 `fetch_open` returns only `OPEN` items; setting a terminal status removes an item from the open queue

## 4. Triage-loop

- [ ] 4.1 `src/platforms/loop.py` — `run_once(orchestrator, platform, hint)`: for each open item → `handle(raw, hint)` → write-back
- [ ] 4.2 Write-back (only when `HandleResult.created`): create case (always), comment the reasoning summary, `set_severity(outcome.priority)`, `set_status(CLOSED if benign/FP else ESCALATED)`
- [ ] 4.3 Skip items that dedup (`created` is False) or that no module resolves (no investigation) — no case/comment/status change

## 5. Wiring & trigger

- [ ] 5.1 Composition root (`api/app.py`): build an `InMemoryTriagePlatform` (dev) and make `run_once` invokable (thin trigger — a `POST /triage/run` route or equivalent); scheduling out of scope
- [ ] 5.2 Confirm `core/` gains no import of `src/platforms/`

## 6. Tests & verify

- [ ] 6.1 `InMemoryTriagePlatform` unit tests: `fetch_open` filters to `OPEN`; terminal status removes items
- [ ] 6.2 `run_once` loop test (mocked analyst): benign → case + `CLOSED`; true-positive → case + `ESCALATED`; each writes comment + severity
- [ ] 6.3 Idempotency: re-running the loop over an already-triaged item produces no new case/comment/status change
- [ ] 6.4 Dependency-direction check: nothing in `src/core/` imports `src/platforms/`
- [ ] 6.5 `make test` green, `make lint` clean
- [ ] 6.6 Update `AGENT.md` / `README.md` — add the Platform primitive to the architecture

## 7. Deferred (out of scope — noted in design)

- [ ] 7.1 `ElasticSecurityPlatform` implementation + the "what is writable in Elastic" spike (`set_severity`, comment/case targeting) — the `elastic-triage-platform` change
- [ ] 7.2 Scheduling/daemonizing the loop for 24/7 operation
