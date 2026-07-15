## Why

Benny today only reads and reasons: an alert comes in via `POST /investigate`, he produces an `Investigation`, and it dies as an HTTP response. The value in a real SOC is the **write-back** — annotate the alert, disposition it, open a case, escalate the real threats. Benny needs *hands*, and they must be portable: DFINITY runs Elastic Security, other environments run something else.

This change introduces the **`TriagePlatform`** — a third architectural primitive alongside modules (reasoning) and capabilities (evidence). A platform is the **operational system Benny works within**: it supplies the work (alerts to triage) and receives his actions (comments, disposition, cases). It is Benny's only surface that mutates the outside world, so it is isolated, permission-scoped, and mockable.

**Scope:** this change delivers *only the abstraction and how it works with Benny* — the `TriagePlatform` interface, the orchestrator triage-loop that drives it, and an in-memory reference implementation for dev/tests. Concrete platform implementations (Elastic Security) are a **follow-up change and explicitly out of scope.**

## What Changes

- **`TriagePlatform` interface (the new primitive).** A Protocol bundling intake + tracking + write-back:
  - **Intake / tracking:** `fetch_open() -> list[work item]` (only items still needing triage), `get(id)`. Tracking lives in the platform via status — Benny keeps **no cursor and no state**; `fetch_open` stops returning an item once it's marked triaged.
  - **Write-back:** `comment(id, text)`, `set_severity(id, severity)`, `set_status(id, status)`, `create_case(id, investigation) -> case_id`.
- **Orchestrator triage-loop.** A `run_once(platform, hint)` pass: `fetch_open → orchestrator.handle(item) → write-back`. Idempotency (dedup by the module's key) makes re-seen items safe. Write-back is **case-always** for traceability:
  - create a case, comment Benny's reasoning, set severity from the investigation's `outcome.priority`
  - **close** the case immediately on `false_positive`/`benign` (noise cleared, trail kept); leave it **open/escalated** on `true_positive`. Benny becomes L1 auto-triage: clears the noise floor, hands humans only real threats, with an audit trail on everything.
- **Driven by the generic `outcome`** (disposition + priority) — the write-back is domain-agnostic and will serve VM findings once VM gets its own platform.
- **In-memory reference `TriagePlatform`** — holds items + records actions in memory, so the whole loop is testable end-to-end without any external system.
- **Modules stay pure.** Reasoning produces an `Investigation`; the triage-loop performs all side effects. Modules and capabilities are untouched.

## Capabilities

### New Capabilities
- `triage-platform`: the `TriagePlatform` interface (intake + tracking + write-back), the triage-loop (`run_once`) with case-always/auto-close, and an in-memory reference implementation — all self-contained under `src/platforms/`

### Modified Capabilities
- None. The loop *consumes* the existing `OrchestratorAgent.handle()` unchanged; `agent-orchestration` is untouched, and `core/` gains no dependency on the platform layer.

### Non-Goals
- **`ElasticSecurityPlatform`** and any real integration — the follow-up `elastic-triage-platform` change (incl. the "what is actually writable in Elastic" spike for `set_severity`)
- **Scheduling / daemonization** of the loop — `run_once` is the unit; a periodic runner is a thin wrapper deferred to deployment
- Remediation of any kind (block/isolate/disable) — the platform is scoped to triage metadata + cases only
- Conversational MCP / `query`/`recall` (separate `conversational-orchestration` change)

## Impact

- **Depends on:** the merged transition (orchestrator, idempotency, the generic `outcome`)
- **New self-contained `src/platforms/` package** — the third primitive, holding its abstraction, loop, and implementations together (mirroring how `capabilities/data/` keeps `base_data_agent.py` alongside its impls):
  - `base.py` — the `TriagePlatform` Protocol (the abstraction)
  - `loop.py` — `run_once(orchestrator, platform, hint)`: fetch → `handle()` → write-back, incl. the `outcome`→platform mapping (case-always, auto-close/escalate)
  - `memory.py` — `InMemoryTriagePlatform` reference impl (dev/tests)
- **Dependency direction is inward only:** `platforms/ → core` (imports `OrchestratorAgent`) and `platforms/ → schemas`. `core/` gains **no** dependency on `platforms/` — the loop lives in `platforms/` precisely so core stays unaware of it. The loop is domain-agnostic (touches only `handle(raw, hint)` and the generic `outcome`/`report`).
- Tests: the in-memory platform drives the loop end-to-end (fetch → investigate → case created, commented, severity set, closed/escalated by verdict)
- **Permission boundary (documented):** the platform is Benny's sole write surface, scoped to triage metadata + cases — never remediation. Concrete impls get API grants scoped to exactly that.
- No changes to modules, capabilities, or `core/`; REST `/investigate` and `/findings` remain the request-driven path. The composition root (`api/app.py`) builds the platform impl and triggers `run_once`; scheduling stays out of scope.

### Open questions (for design)
- Does the loop route by a hint (MVP: one platform → `siem`) or by the work item's shape (`accepts()`)? MVP leans hint.
- `fetch_open` returns raw payloads (module builds the typed input) vs typed items — leaning raw, to keep the platform decoupled from module schemas.
- Case-severity vs alert-severity semantics — deferred to the Elastic follow-up spike; the interface just declares `set_severity`.
