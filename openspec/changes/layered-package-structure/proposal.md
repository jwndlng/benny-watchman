## Why

`modular-soc-architecture` made the **horizontal/vertical** seam visible (`core/` / `capabilities/` / `modules/`), but a second axis stayed hidden and the tree has since accreted:

- **`capabilities/` mixes two boundary kinds.** `data/` and `enrichment/` are **LLM sub-agents**; `identity/` is a **deterministic composite tool**. Those are different units under the project's own compression-boundary rule, but the folder hides the distinction — the same mixing repeats inside modules.
- **Modules aren't self-contained.** A module's domain models sit next to its analyst, but there's no consistent home for them, and VM's `intel` tool has no obvious place.
- **The I/O edges are flat peers.** `api/`, `mcp/`, `platforms/`, `engines/`, `models.py` sit at the `src/` root as siblings of `core/`, so the layering (what's *pure framework* vs what *touches the outside world*) is invisible — and "is this core?" has no mechanical answer.
- **Dead scaffolding adds noise.** `EnrichmentAgent`, `ReviewerAgent`, and `DetectionEngineerAgent` are defined but never instantiated, sitting beside live code with no signal.

This is a **behavior-preserving refactor**: relocations, import rewrites, and three deletions — no new abstractions, no API/MCP/runtime changes. Doing it before the tree grows (more modules, more tools) keeps the agent-boundary taxonomy legible.

## What Changes

Evolve the package layout so **both** organizing axes are legible — *where is it shared?* (horizontal/vertical) **and** *what kind of unit is it?* (sub-agent / tool / adapter):

- **Split `capabilities/` by boundary kind** into `capabilities/subagents/` (LLM loops — `data/`) and `capabilities/tools/` (deterministic composites — `identity/`). This encodes the compression-boundary rule in the filesystem.
- **Make modules self-contained packages.** Each module owns its domain models under `<module>/schemas/` and its module-local tools under `<module>/tools/` (e.g. VM's `intel`). `capabilities/` stays **purely horizontal** — cross-domain skills only. A module-local tool is promoted to `capabilities/` only when a second module needs it.
- **Introduce the `adapters/` ring.** Group the outer I/O edges — `api/`, `mcp/`, `platforms/`, `engines/`, and persistence (`models.py` → `adapters/persistence.py`) — under `src/adapters/`. These depend inward on `core/`; `core/` never imports them.
- **Delete the unwired stubs** — `capabilities/enrichment/`, `modules/siem/reviewer.py`, `modules/siem/detection_engineer.py`.

The result: "where does this go?" has one mechanical answer. *Touches the outside world →* `adapters/`; *shared skill →* `capabilities/{subagents,tools}`; *domain-specific →* the module (`schemas/` or `tools/`); *pure orchestration →* `core/`.

## Capabilities

### Modified Capabilities
- `project-structure`: the horizontal/vertical seam gains a second axis (sub-agent vs tool), modules become self-contained (own their `schemas/` and `tools/`), and the outer I/O edges are grouped under an `adapters/` ring. Still a behavior-preserving relocation — no new abstractions.

### Non-Goals
- **No behavior change** — no API/MCP surface change, no runtime change, no schema reshaping. Tests pass with only import-path updates.
- **No new modules or capabilities** — this is layout only.
- **Not extracting the engine *port* into `core/`** — `capabilities/subagents/data` will still depend on `adapters/engines` (as it does today). Threading the `QueryEngine` interface into `core/` so data agents depend on the port, not the adapter, is a flagged future refinement.
- **Not renaming the `…Capability` tool suffix** (the `capabilities/` folder vs `Capabilities` container vs `…Capability` class overload) — a legibility nicety deferred to keep this diff mechanical.

## Impact

- **New top-level package:** `src/adapters/` (absorbs `api/`, `mcp/`, `platforms/`, `engines/`, persistence). New sub-packages: `capabilities/subagents/`, `capabilities/tools/`, `modules/<m>/schemas/`, `modules/<m>/tools/`.
- **Moves:**
  - `capabilities/data/*` → `capabilities/subagents/data/*`
  - `capabilities/identity/*` → `capabilities/tools/identity/*`
  - `modules/siem/{alert,incident_report}.py` → `modules/siem/schemas/`
  - `modules/vuln_mgmt/{finding,report}.py` → `modules/vuln_mgmt/schemas/`
  - `modules/vuln_mgmt/intel.py` → `modules/vuln_mgmt/tools/intel.py`
  - `api/`, `mcp/`, `platforms/`, `engines/` → `adapters/{api,mcp,platforms,engines}/`
  - `models.py` → `adapters/persistence.py`
- **Deletions:** `capabilities/enrichment/`, `modules/siem/reviewer.py`, `modules/siem/detection_engineer.py`.
- **Dependency rule after the move:** `core → schemas`; `capabilities → core, adapters/engines`; `modules → core, capabilities, schemas` (never another module); `adapters → core, capabilities, modules` (the composition root, `adapters/api/app.py`, wires all).
- **`main.py`** changes one import to `src.adapters.api.app`.
- **Behavior-preserving** — exit check is `make test` green + `make lint` clean with changes limited to import paths and the three deletions.
