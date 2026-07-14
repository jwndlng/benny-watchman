## Why

The architecture leans heavily on multi-agent delegation, and the dominant cost driver is the context re-sent on every turn (a single agent's cost grows ~quadratically with its tool-call turns). Without a written rule, the agent tree quietly becomes an expensive N-deep nest. The compression-boundary rule and the horizontal/vertical model should be codified as durable project guidance that outlives any single change and is present where code is written.

## What Changes

- **Codify the compression-boundary rule** as project guidance (in `CLAUDE.md` and/or a docs file):
  - Agent boundaries are compression boundaries — put one wherever multiple round-trips would otherwise accumulate in a parent's expensive context.
  - Make a boundary an **LLM sub-agent** only when it *both* compresses parent context *and* needs reasoning (a model decides the control flow or synthesizes a judgment).
  - A **fixed pipeline** of deterministic calls is a **composite tool**, not an agent.
  - A **single call** is an **inline tool**.
  - The investigation's own top-level reasoning is the analyst's job and is **never sharded**.
  - "Needs reasoning" ≠ "has a parameter."
- **Codify the horizontal/vertical model** — analyst *modules* (verticals) over shared *capability* agents/tools (horizontals), under an OrchestratorAgent, with the node-type decision table.
- Doc-only; no code change. Landed early so subsequent slices are written against the rule.

## Capabilities

### New Capabilities
- `agent-cost-principles`: written project guidance — the compression-boundary rule, the horizontal/vertical model, and the node-type decision table (inline tool / composite tool / sub-agent / analyst)

### Modified Capabilities
- None

## Impact

- **Depends on:** nothing — can land anytime; recommended early (before the module-contract work) so it guides those slices
- `CLAUDE.md` (and/or `docs/`): add the principles and the decision table
- No runtime impact; this is guidance, not code
