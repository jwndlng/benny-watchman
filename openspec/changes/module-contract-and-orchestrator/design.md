## Context

Slice 1 (`modular-soc-architecture`) relocated code into the `core/ · capabilities/ · modules/` seam but introduced no abstractions. The deterministic `Orchestrator` in `core/orchestration/` still imports the SIEM `AnalystAgent`, `Alert`, and `Investigation` directly — the one transitional `core → modules` edge that slice 1 explicitly allowed.

This change introduces the module abstraction, a module registry, an agentic orchestrator, and a capability registry, then migrates SIEM to be the first module through the contract — removing that edge. The four architectural decisions (router-now, two-speed entry, typed Protocol, Capabilities registry) are already settled in the `modular-soc-architecture` design. This document is the implementation approach and the refinements that surface when turning those decisions into code.

## Goals / Non-Goals

**Goals:**
- A typed `AnalystModule` contract and a `ModuleRegistry`
- An `OrchestratorAgent` with a single `handle()` seam and two-speed routing
- A typed `Capabilities` container injected into modules
- SIEM wrapped as the first module; the transitional `core → modules` edge removed
- Behavior parity for the existing SIEM `/investigate` flow (same reports, existing tests green)

**Non-Goals:**
- Investigation idempotency / dedup — `dedup_key` and the persistence reshape stay in `investigation-idempotency`
- Identity as a formal capability — slice 2 keeps the `OktaClient` / `lookup_user` wiring, just injected via `caps` (`identity-capability` formalizes it)
- Cross-module synthesis (lead-analyst) — router only
- A second module (`vuln-management-module`)
- Free-form chat→investigation as a product path — the no-hint classification path is built and unit-tested but only meaningfully exercised once a second module exists

## Decisions

### D1. `AnalystModule` is a typed Protocol; the orchestrator-facing method is `investigate(inp, caps)`
The orchestrator's need is "given a module + a raw input → an `Investigation`." So the public contract is `investigate`, not a standalone `build_analyst`. Wiring the analyst from capabilities (the parent design's "build_analyst(caps)" idea) becomes a *module-internal* step, because the SIEM analyst's persona depends on the matched runbook — which requires the input.

```python
class AnalystModule(Protocol[TInput]):
    name: str
    input_type: type[TInput]                                    # Alert
    def accepts(self, raw: dict) -> bool                        # free-form routing
    def investigate(self, inp: TInput, caps: Capabilities) -> Investigation
```

`dedup_key` is intentionally **not** added here — it is introduced by `investigation-idempotency`, the change that consumes it, to avoid a dead method now. The Protocol grows one facet per change.

*Alternative considered:* `build_analyst(caps)` as the contract method, pushing runbook matching into the analyst per-call. Rejected — it forces restructuring `AnalystAgent` and yields a less direct orchestrator contract.

### D2. `ModuleRegistry` is new and module-level; runbook selection stays inside the SIEM module
`ModuleRegistry` holds `AnalystModule`s and resolves one by name (a hint) or by `accepts()` (free-form). This is **not** a rename of `RunbookRegistry`: runbook matching is a within-SIEM concern (choosing the analyst persona per `alert.type`), so `RunbookRegistry` stays and becomes SIEM-internal — the SIEM module loads `modules/siem/runbooks/` and matches per investigation. Two registries at two levels.

*Alternative considered:* fold runbooks into `ModuleRegistry`. Rejected — conflates module routing with within-module playbook selection.

### D3. `OrchestratorAgent`: one `handle()` seam, two speeds
`handle(raw, hint=None) -> Investigation`: a `hint` present → `registry.get(hint)`; absent → `registry.resolve(raw)` (via `accepts()`, falling back to an LLM classifier over module names/descriptions once ≥2 modules exist). Then `module.investigate(module.input_type(**raw), caps)`, persist, return. Router-only: it returns a single module's `Investigation`, and the return type is deliberately left able to carry a synthesized multi-module result later. The SIEM `/investigate` route passes `hint="siem"`.

*Alternative considered:* always-agentic classification. Rejected per parent decision 2 — an LLM hop on the explicit-domain hot path is wasteful.

### D4. `Capabilities`: a typed container built at the composition root
A thin typed container of configured instances — `data: dict[str, BaseDataAgent]`, `identity` (the `OktaClient`/lookup for now), `enrichment` (later) — built once in `create_app` and passed into `module.investigate(inp, caps)`. Modules select what they consult (`caps.data["security_logs"]`). Because identity flows through `caps`, the later `identity-capability` change can swap the implementation without touching any module signature.

### D5. SIEM as the first module, and edge removal
Add `SIEMModule` in `modules/siem/` implementing the contract: `input_type = Alert`, `accepts()` = alert-shaped payload, `investigate()` = match runbook → construct `AnalystAgent(runbook, data_agents=caps.data[...], okta_client=caps.identity)` → run → `Investigation`. Registration happens at the **composition root** (`create_app`), which is allowed to import both `core` and `modules`. `OrchestratorAgent` and `ModuleRegistry` no longer import `AnalystAgent`/`Alert`, so the transitional `core → modules` edge disappears — only the bootstrap imports modules.

## Risks / Trade-offs

- **Over-abstraction with a single module** → Keep the Protocol minimal (only what slice 2 uses); `accepts()`/classifier stay trivial until VM proves them.
- **Behavior drift in the SIEM flow** → Parity is the acceptance bar: existing SIEM `/investigate` tests pass unchanged, plus a new test asserting the flow runs through `OrchestratorAgent` + `SIEMModule`.
- **`Capabilities` becomes a god-object** → It is a typed container of instances, not logic; all wiring stays in the composition root.
- **LLM classifier cost on the chat path** → Not exercised in slice 2 (one module); revisit when VM lands.
- **Loosely-typed raw input** → `module.input_type(**raw)` validates via Pydantic, so a malformed payload raises before the analyst runs.

## Migration Plan

1. Add core contracts (`AnalystModule`, `ModuleRegistry`, `Capabilities`) — no behavior change yet (additive).
2. Add `SIEMModule` wrapping the current `AnalystAgent` flow (runbook match + analyst construction).
3. Replace `Orchestrator` with `OrchestratorAgent` using the registry; wire `create_app` to build `Capabilities` and register `SIEMModule`.
4. Point `/investigate` at `OrchestratorAgent.handle(raw, hint="siem")`.
5. Delete the direct `AnalystAgent` import from `core/orchestration/`; run the suite for parity.

**Rollback:** steps 1–2 are additive; if step 3/4 regresses, revert the orchestrator swap to restore the deterministic path while keeping the new contracts in place.

## Open Questions

- Exact request shape for the free-form path (plain text vs structured) — deferred until the chat/VM path needs it.
- Where the classifier's module descriptions live (a `description` on the module?) — add when the second module lands.
- Whether `investigate()` should return a full `Investigation` or a lighter report the orchestrator wraps — leaning `Investigation` for parity now; revisit in `investigation-idempotency`, which reshapes `Investigation` anyway.
