## Why

Today Benny's MCP surface bypasses the brain: `list_runbooks` and a single-shot `lookup_data` that fans out to data agents. Meanwhile the domain-expert modules (SOC/SIEM, VM) are reachable only by *formal triage* — a structured alert/finding in, a persisted verdict out.

The product vision is a **team of security experts you can talk to**: ask what they *know* (hunt a hypothesis, "top 10 vulns to fix"), ask what they *did* (past investigations and verdicts) — not just hand them alerts. Threat hunting, specifically, is not a new component: it is the SOC expert working a hypothesis in free-form rather than reacting to an alert.

This change routes MCP through the `OrchestratorAgent` and gives every module a free-form conversational capability. It sets up — but does not build — the "lead-analyst" cross-domain synthesis that the orchestrator's `handle()` seam was designed for from the start.

## What Changes

- **Modules become full domain experts.** Alongside `investigate(input) → Investigation` (reactive triage; dedup + persist), each module gains two free-form capabilities:
  - **`query`** — reason over the **facts**: the data capabilities (logs, asset inventory) **including alerts** (an alert is a fact — "a detection fired" — and hunting needs to correlate it with logs). Threat hunting lives here (SOC module in `query` mode); "top 10 vulns to fix" is answered here (VM module in `query` mode).
  - **`recall`** — reason over Benny's **own conclusions**: the persisted Investigations this module produced ("what did you triage on host-01, and what verdict?").
- **Facts vs. opinions is the organizing line.** `query` reaches facts (incl. alerts); `recall` reaches Benny's opinions (its Investigations). The same alert legitimately appears on both sides — the detection is a fact (`query`), Benny's verdict on it is an opinion (`recall`).
- **MCP routes through the `OrchestratorAgent`** (no more bypass). First-class tools: `query` (facts) and `investigations`/`recall` (conclusions), plus optional semantic sugar (`alerts`, `vulnerabilities`) as discoverable lenses over the data plane — not a partition of it. The orchestrator classifies a free-form request to the right expert, activating the `handle(raw, hint=None)` "no-hint → classify" branch that already exists.
- **Persistence gains lookups** by module (and by entity, e.g. asset) so a module can answer "what did you do on X".
- **Threat hunting is emergent**, not a separate module — it is the SOC module's `query` persona. This supersedes the separately-discussed ThreatHunter module.
- **Escalation loop:** a `query`/hunt that surfaces a lead can be escalated into a formal `investigate` (alert/finding) — the discovery front-end feeding the triage back-end.

## Capabilities

### New Capabilities
- `conversational-orchestration`: free-form `query`/`recall` on modules, MCP routed through the orchestrator, and the facts-vs-opinions tool taxonomy

### Modified Capabilities
- `analyst-module-contract`: modules gain `query` and `recall` alongside `investigate()`; triage-only vs hunt-capable split resolved via a base `Module` + `TriageMixin` (open question)
- `agent-orchestration`: the `handle()` free-form branch resolves a natural-language request to a module's `query`/`recall` (single-module routing for now)

### Non-Goals
- **Lead-analyst cross-module synthesis** — fanning a cross-domain question ("posture of host-01?") to SOC + VM and weaving alerts + vulns + each expert's history into one answer. Deferred as the explicit follow-up; this change is its prerequisite.
- Server-side session/conversation state — the MCP client (the CLI) holds the conversation; each tool call is a self-contained reasoning turn
- Real external data sources / intel (dev-stub continues)
- Remediation (Benny stays investigation-only)

## Impact

- **Depends on:** the merged transition (module contract, orchestrator, capability layer, idempotency envelope)
- `src/core/orchestration/module.py`: add `query` / `recall` to the module contract (or a base `Module` + `TriageMixin`)
- `src/modules/siem/`, `src/modules/vuln_mgmt/`: implement `query` (data/hunt persona) and `recall` (own history); likely a second persona set (hunt/query vs triage runbooks)
- `src/core/orchestration/orchestrator.py`: `handle()` free-form branch → `module.query`/`recall`; the return type already allows the later synthesized result
- `src/mcp/server/`: replace the bypass tools with `query` + `investigations`/`recall` routed through the orchestrator; optional `alerts`/`vulnerabilities` sugar
- `src/models.py`: add by-module / by-entity Investigation lookups
- No breaking change to the REST triage path; the MCP surface changes

### Open questions (carried from discussion)
- One `query()` reasoning over facts + history, or a `query`/`recall` split? (Leaning split — facts vs opinions.)
- Does Benny ingest an alerts *data source*, or is "alerts Benny knows" == its Investigations?
- Base `Module` + `TriageMixin` so a hunt-only capability need not stub `investigate()`?
