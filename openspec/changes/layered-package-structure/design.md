## Context

`modular-soc-architecture` established the horizontal/vertical seam but left a second axis implicit, and the tree has since grown edges (`platforms/`, richer `mcp/`) as flat root peers. This change is a **behavior-preserving refactor** that makes the layering mechanical. No runtime, API, or MCP-surface change.

## Two orthogonal axes

The structure is hard to reason about because only one axis is encoded today.

```
Axis 1 — WHERE is it shared?   horizontal (capabilities, core) vs vertical (modules)   [encoded]
Axis 2 — WHAT kind of unit?    LLM sub-agent vs deterministic tool vs I/O adapter        [NOT encoded]
```

Axis 2 is the project's own compression-boundary rule (sub-agent = LLM loop that reasons + compresses; composite tool = fixed pipeline; adapter = I/O edge). Making it visible in the filesystem is the core of this change.

## Target layout

```
src/
├── core/                     FRAMEWORK — pure; imports only schemas/ (+ stdlib/3p)
│   ├── agents/base_agent.py
│   └── orchestration/        orchestrator, module (Protocol), *_registry, capabilities (container)
│
├── capabilities/             HORIZONTAL skills — cross-domain only
│   ├── subagents/            LLM loops         ── boundary: "sub-agent"
│   │   └── data/             base_data_agent, sqlite_, elastic_, query_tool
│   └── tools/                deterministic     ── boundary: "composite tool"
│       └── identity/         assessment (IdentityCapability), okta, user_profile
│
├── modules/                  VERTICAL domains — self-contained packages
│   ├── siem/     { analyst.py · module.py · schemas/{alert,incident_report} · runbooks/ }
│   └── vuln_mgmt/{ analyst.py · module.py · schemas/{finding,report} · tools/intel.py · runbooks/ }
│
├── adapters/                 OUTER RING — touch the world, depend inward
│   ├── api/                  app.py (composition root), routes/, schemas/
│   ├── mcp/                  server/, clients/
│   ├── platforms/            base, memory, elastic, loop
│   ├── engines/              base, sqlite, elasticsearch
│   └── persistence.py        (was models.py)
│
└── schemas/  config.py  utils/    LEAF — shared envelopes + infra, no upward deps
```

## Decision procedure ("where does this go?")

Applied in order, first match wins:

1. **Touches an external system** (DB, Kibana, HTTP, MCP transport, on-disk store)? → `adapters/`.
2. **Domain-specific** to one module (its models, its own tools/analyst)? → `modules/<m>/{schemas,tools}/` or the module root.
3. **A skill shared across ≥2 domains?** → `capabilities/subagents/` (if an LLM loop) or `capabilities/tools/` (if deterministic).
4. **Pure orchestration / agent framework?** → `core/`.
5. **A plain shared data type or config?** → `schemas/` / `config.py` / `utils/`.

## Resolved decisions

- **Module-local tools stay in the module** (e.g. VM's `intel` → `modules/vuln_mgmt/tools/`). This keeps a module a self-contained package and preserves the horizontal/vertical seam: `capabilities/` is *horizontal-only*. A module tool is **promoted** to `capabilities/tools/` only when a second module consumes it. (Rejected: a single "shared toolbox" holding all tools regardless of scope — it makes modules non-self-contained and blurs the seam.)
- **Group the I/O edges under `adapters/`** rather than leaving them as root peers or folding them into `core/`. Folding into core would invite `core → adapter` imports and destroy the swappability the `TriagePlatform`/`QueryEngine` abstractions exist for. Naming the ring gives the "high-level grouping" without breaking the inward dependency rule.

## Dependency rule (post-move)

```
schemas / config / utils   →  (nothing)                      leaf
core                       →  schemas  (+ 1 typing edge, below)
capabilities               →  core, adapters/engines
modules                    →  core, capabilities, schemas    (never another module)
adapters                   →  core, capabilities, modules    (adapters/api/app.py wires all)
```

Two arrows violate strict hexagonal purity; **both exist today and are relocated, not introduced**:

- `capabilities/subagents/data → adapters/engines` — the DataAgent imports `QueryEngine` (runtime).
- `core/orchestration → adapters/persistence` — a `TYPE_CHECKING`-only import of `InvestigationModel` used as the DI type hint for the orchestrator's injected `persistence` param (the instance is built at the composition root, never imported at runtime by core).

Both are the same shape: core-ish code type-hinting a concrete adapter instead of a port. Confining them to `core/orchestration/` (persistence) and `capabilities/subagents/data/` (engines) keeps the leak isolated; extracting the ports is Deferred.

## Migration approach

Purely mechanical; the risk is import breakage, not logic.

1. **Baseline**: `make test` green + `make lint` clean is the behavior-preservation reference.
2. **Move with history**: use `git mv` so blame survives; create new packages with `__init__.py`.
3. **Rewrite imports**: the moves are a fixed rename map (`src.engines` → `src.adapters.engines`, `src.platforms` → `src.adapters.platforms`, `src.models` → `src.adapters.persistence`, `src.capabilities.data` → `src.capabilities.subagents.data`, `src.capabilities.identity` → `src.capabilities.tools.identity`, `src.modules.siem.alert` → `src.modules.siem.schemas.alert`, `src.modules.vuln_mgmt.intel` → `src.modules.vuln_mgmt.tools.intel`, etc.). Apply the map across `src/`, `tests/`, `main.py` with a scripted find/replace, then let `ruff` catch stragglers (unused/unresolved imports).
4. **Config defaults & docs**: update `RUNBOOKS_PATH`/`VULN_RUNBOOKS_PATH` only if the module paths move (they don't — runbooks stay under the module), and update CLAUDE.md / README / AGENT.md structure references.
5. **Deletions**: remove the three unwired stubs and their tests/registrations (there are none wired, so this is a straight delete).
6. **Verify**: `make test` (same pass count) + `make lint` + a grep-based dependency-direction check (`core/` imports no `modules/`/`adapters/`; `capabilities/` imports no `modules/`).

Order matters only in that new `__init__.py` packages must exist before imports resolve; otherwise the rename map is applied atomically in one pass.

## Deferred (explicit non-goals)

- **Extract ports into `core/`** for the two isolated exceptions above — a `QueryEngine` port (so `capabilities/subagents/data` depends on an interface, not `adapters/engines`) and a persistence port (so `core/orchestration` type-hints an interface, not `adapters/persistence.InvestigationModel`). Both remove inward-rule leaks but introduce abstractions, so they're out of scope for this pure move.
- **Rename the `…Capability` tool suffix** (`IdentityCapability` → `IdentityTool`, etc.) to disambiguate from the `capabilities/` folder and `Capabilities` container. A legibility nicety; deferred to keep this diff a pure move.

## Risks

- **Import cycles** surfacing when packages split — mitigated by the strict inward rule; if one appears, it signals a misplaced file (fix placement, not add a shim).
- **Wide diff** touching most files' import lines — mitigated by `git mv` (preserves blame) and the scripted rename map (mechanical, reviewable as a rename set).
- **Stale references in docs/CLAUDE.md** — included in the task list so guidance doesn't drift from the tree.
