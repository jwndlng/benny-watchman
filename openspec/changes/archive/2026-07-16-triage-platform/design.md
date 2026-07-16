# Design: TriagePlatform

## Context

Benny reads and reasons but never acts: an investigation ends as an HTTP response. The value in a SOC is the write-back — annotate the alert, disposition it, open a case, escalate the real ones. `TriagePlatform` is the **operational I/O boundary**: it supplies the work (alerts to triage) and receives Benny's actions. It's a third architectural primitive next to modules (reasoning) and capabilities (evidence), and the only surface that mutates the outside world.

This change delivers the **abstraction + the loop that drives it + an in-memory reference implementation**, all self-contained under `src/platforms/`. Concrete platforms (Elastic Security) are a follow-up (`elastic-triage-platform`).

## Goals / Non-Goals

**Goals:**
- A `TriagePlatform` Protocol: intake + tracking + write-back
- A domain-agnostic triage-loop (`run_once`) that fetches from a platform, delegates to `OrchestratorAgent.handle()`, and writes results back (case-always; auto-close benign, escalate real)
- An `InMemoryTriagePlatform` that makes the loop testable end-to-end with no external system
- `core/` gains no dependency on the platform layer

**Non-Goals:**
- `ElasticSecurityPlatform` and any real integration (+ the "what's writable in Elastic" spike) — follow-up
- Scheduling/daemonizing the loop — `run_once` is the unit; a periodic runner is a deployment wrapper
- Remediation (block/isolate/disable) — the platform is scoped to triage metadata + cases
- Conversational MCP (`query`/`recall`) — separate change

## Decisions

### D1. The `TriagePlatform` Protocol
```python
class TriageStatus(str, Enum):
    OPEN = "open"          # needs triage
    ESCALATED = "escalated" # true-positive → left for a human
    CLOSED = "closed"       # benign/false-positive → auto-closed by Benny

class TriagePlatform(Protocol):
    def fetch_open(self, limit: int = 50) -> list[dict]: ...      # raw work items still needing triage
    def get(self, item_id: str) -> dict | None: ...
    def comment(self, item_id: str, text: str) -> None: ...
    def set_severity(self, item_id: str, severity: str) -> None: ...
    def set_status(self, item_id: str, status: TriageStatus) -> None: ...
    def create_case(self, item_id: str, investigation: Investigation) -> str: ...  # -> case id
```
- **Raw dict work items**, not typed module inputs — the platform stays decoupled from `modules/*` schemas; the orchestrator/module validates. Each item MUST carry an `id`.
- **Tracking lives in the platform:** `fetch_open` returns only `OPEN` items; once Benny sets a terminal status the item stops coming back. Benny keeps no cursor and no state.

### D2. The triage-loop (`run_once`)
```python
def run_once(orchestrator, platform, hint) -> list[Investigation]:
    for raw in platform.fetch_open():
        result = orchestrator.handle(raw, hint=hint)     # HandleResult(investigation, created)
        if result.investigation is None or not result.created:
            continue                                     # unresolved, or dedup hit → don't re-write
        inv = result.investigation
        platform.create_case(raw["id"], inv)             # case ALWAYS (traceability)
        platform.comment(raw["id"], _summarize(inv))
        platform.set_severity(raw["id"], inv.outcome.priority)
        platform.set_status(raw["id"],
            CLOSED if _benign(inv.outcome.disposition) else ESCALATED)
```
- **Case-always** → every alert leaves a trail; benign/FP is created-and-closed, real threats stay escalated. Benny is L1 auto-triage.
- **Write-back only on `created`** — the idempotency `created` flag means a re-seen alert isn't re-commented/re-cased.
- **Driven by the generic `outcome`** (disposition + priority) → the loop is domain-agnostic and will serve VM findings unchanged.

### D3. Location — self-contained `src/platforms/`
```
src/platforms/
  base.py     # TriageStatus + TriagePlatform Protocol
  loop.py     # run_once(orchestrator, platform, hint) + write-back mapping
  memory.py   # InMemoryTriagePlatform
```
Dependency is inward only: `platforms/ → core` (`OrchestratorAgent`) and `platforms/ → schemas` (`Investigation`/`outcome`). `core/` never imports `platforms/`. Mirrors how `capabilities/data/` keeps `base_data_agent.py` beside its impls.

### D4. `InMemoryTriagePlatform`
Seeded with a list of raw work items; keeps an in-memory status per item and records comments/severities/cases. `fetch_open` filters to `OPEN`. Lets a test assert the full loop: fetch → investigate → case created + commented + severity set + status flipped by verdict.

### D5. Permission boundary
The platform is Benny's sole write surface, scoped to triage metadata + cases — never remediation. Concrete impls receive API grants scoped to exactly that; the abstraction encodes no destructive action.

## Risks / Trade-offs

- **`set_severity` semantics vary by platform** → the interface just declares it; the Elastic follow-up spikes whether it maps to case severity, alert severity, or a workflow tag.
- **Write-back partial failure** (case created, comment fails) → for MVP, best-effort with logging; a real platform should make it as atomic as its API allows. Note it, don't over-engineer now.
- **`comment`/`set_severity` target (alert vs case)** → the interface is item-id-keyed; the impl decides where it lands (likely the case in Elastic). Kept out of the abstraction.

## Migration Plan

1. `platforms/base.py` — `TriageStatus` + `TriagePlatform` Protocol.
2. `platforms/memory.py` — `InMemoryTriagePlatform`.
3. `platforms/loop.py` — `run_once` + outcome→platform mapping.
4. Tests — drive the loop with the in-memory platform (case-always, close-benign, escalate-real, dedup-no-rewrite).
5. Composition root — build the in-memory platform and expose `run_once` (a thin trigger; scheduling deferred).

## Open Questions

- Trigger surface for `run_once` — a `POST /triage/run` endpoint vs a CLI vs a background task? MVP can expose the callable; the trigger is a thin deployment choice.
- Batch size / ordering of `fetch_open` — default `limit`, oldest-first; revisit under real volume.
- Whether `comment`/`set_severity` should take the returned `case_id` rather than the item id — deferred to the Elastic impl once we know where they land.
