# Design: Benny as a modular SOC engineer

## Context

Benny should become a general security analyst that acquires new triage domains as **modules** ("skills"), reachable two ways:

- **Direct task (API):** `POST /investigate` with a concrete, typed input — the domain is explicit.
- **Conversation (MCP):** an external agent (Claude Code, Antigravity) asks Benny in natural language — the domain must be inferred. Starts as simple tool calls; evolves toward "send a query to Benny, get an answer."

The next domain is Vulnerability Management triage, which is *structurally the same shape* as SIEM alert triage (investigate an input against playbooks + corporate context, reach a verdict) but shares almost none of the concrete tooling. That mismatch — same shape, different tools — is what the architecture must express.

## The core model: horizontal vs vertical agents

Two kinds of agents, governed by opposite forces.

```
  VERTICAL  — "analyst modules" (skills): own a triage DOMAIN end-to-end
  ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
  │ SIEM Analyst     │   │ VM Analyst       │   │ (future modules) │   diverge on purpose:
  │ playbooks+output │   │ playbooks+output │   │                  │   different tooling
  └────────┬─────────┘   └────────┬─────────┘   └──────────────────┘
           │  consult             │  consult
           ▼                      ▼
  ═════════════════════════════════════════════════════════════════════
  HORIZONTAL — "capabilities": own a cross-cutting COMPETENCE            converge on purpose:
  ┌────────────┐  ┌────────────┐  ┌──────────────┐                      shared by all modules
  │ Identity   │  │ Data       │  │ Enrichment   │
  │ who/what   │  │ query the  │  │ what's known │
  │ can access │  │ logs/assets│  │ about an IOC │
  └────────────┘  └────────────┘  └──────────────┘
```

Full request path, with the OrchestratorAgent on top:

```
  ┌─ REST /investigate (explicit domain) ─┐   ┌─ MCP (chat: "ask Benny…") ─┐
  └──────────────────┬────────────────────┘   └──────────────┬─────────────┘
                     └──────────────┬───────────────────────┘
                                    ▼
                         ┌─────────────────────┐
                         │  OrchestratorAgent  │  deterministic when domain known;
                         └──────────┬──────────┘  agentic when it must be inferred
                    ┌───────────────┼────────────────┐
                    ▼               ▼                ▼
              SIEM Analyst     VM Analyst      (future module)      VERTICAL
                    └───────┬───────┴───────┬────────┘
                            ▼               ▼
                    Identity · Data · Enrichment                    HORIZONTAL
                            │
                    Okta · QueryEngines (SQLite/ES/ClickHouse) · VT/CVE/EPSS/KEV
```

The current `Orchestrator` + `RunbookRegistry` + runbook-driven `AnalystAgent` is a **proto** of exactly this. The work is generalization, not a rewrite:
- `RunbookRegistry` → `ModuleRegistry`
- `Orchestrator` (deterministic) → `OrchestratorAgent`
- `AnalystAgent` (single, SIEM-shaped) → per-module analyst
- `lookup_user` method + `OktaClient` → shared **identity capability**
- the `query_{source}` tool-injection pattern → generalized "inject a capability as a tool"

MCP is the **external** seam (Claude Code, Antigravity, "chat with Benny"); in-process Python is the **internal** seam (orchestrator → analysts → capabilities). This resolves the earlier "own project + MCP layer" vs "one project" tension: we get the external MCP surface *and* in-process type safety, because they operate at different boundaries.

## The module contract

A vertical module is the extension point. Conceptually it declares:

| Facet | SIEM | VM (illustrative) |
|---|---|---|
| **Input contract** | `Alert` (type, severity, source) | Finding (CVE, asset, CVSS) |
| **Playbooks** | runbooks matched by `alert.type` | runbooks matched by vuln class |
| **Analyst** | reasoning loop, owns the verdict | reasoning loop, owns the verdict |
| **Output contract** | `IncidentReport` (verdict, SOC actions) | triage report (exploitable?, priority, SLA) |
| **Dedup key + staleness** | `alert.id` (per firing) | `(cve, asset, content-hash)` (per changed finding) |
| **Capabilities used** | data(logs), identity, enrichment(VT) | data(assets), identity, enrichment(CVE/EPSS/KEV) |
| **Post-processing** | DetectionEngineer (draft rules) | (domain-specific, if any) |

The `OrchestratorAgent` discovers modules via a `ModuleRegistry` and routes an incoming request to one. This makes "add a domain" = "add a module folder," not "modify the core." A module is a typed `Protocol` (decision 3 below), registered explicitly at startup:

```python
class AnalystModule(Protocol[TInput, TReport]):
    name: str                              # "siem"
    input_type: type[TInput]               # Alert
    report_type: type[TReport]             # IncidentReport
    def accepts(self, raw: dict) -> bool   # can this module handle this input? (free-form routing)
    def dedup_key(self, inp: TInput) -> str  # idempotency key (see investigation decision)
    def build_analyst(self, caps: Capabilities) -> Analyst  # wired with the capabilities it selects
```

This placement also sorts the existing post-MVP agents cleanly, which is a good validation of the model:
- `EnrichmentAgent` → **horizontal** capability (both domains enrich indicators)
- `DetectionEngineerAgent` → **SIEM module** (drafts detection rules from incident reports — domain-specific)
- `ReviewerAgent` → a horizontal "critic" over analyst output. It can stay horizontal only if it critiques against a base report interface rather than the concrete SIEM `IncidentReport`; otherwise it lives per-module. (Follows from the investigation-envelope decision below.)

## Decision: Investigation is a core idempotency envelope

The goal is that **each alert or finding is reviewed once**. Today this is aspirational, not enforced: `Orchestrator.investigate()` always runs a fresh `AnalystAgent` and persists a record keyed by a random `uuid4`, so submitting the same alert twice produces two investigations. The `PENDING`/`RUNNING` statuses exist in the enum but are never used, and `POST /investigate` returns `202` while running synchronously.

"Review once" is a **horizontal** concern — VM findings need the identical guarantee — so the investigation *record* belongs in `core/`, and only the *report payload* inside it is domain-specific. Within that, responsibilities split:

```
  core owns the MACHINERY                 │  the module owns the POLICY
  ─────────────────────────────────────── │ ───────────────────────────────────
  claim key → run → save → return existing │  what IS the key?
  on repeat; the status lifecycle          │  does a content change bust it?
```

The policy must be module-supplied because SIEM and VM want different dedup semantics:

```
  SIEM:  key = alert.id            each firing is a distinct event → review once per firing;
                                   recurrence arrives as a new alert.id → new investigation.
  VM:    key = (cve, asset, hash)  a finding persists across scans → don't re-triage every scan,
                                   but a content change (now in KEV, CVSS ↑) busts the key → re-review.
```

So the **module's input contract exposes a stable dedup key + staleness rule** (the new contract facet above); `core` provides the claim-by-key machinery. `Investigation` becomes a generic envelope:

```python
Investigation:                    # core envelope, domain-agnostic
    id: str                       # internal id
    key: str                      # module-derived dedup key
    module: str                   # which vertical produced it
    status: PENDING|RUNNING|COMPLETE|FAILED
    created_at / completed_at
    outcome: Outcome | None       # small generic summary (disposition, priority)
    report: <domain payload> | None
```

Two payoffs fall out:
- The unused `PENDING`/`RUNNING` statuses become the **claim lifecycle**: insert a `RUNNING` row keyed by `key` *before* dispatching, so a concurrent duplicate submit sees the in-flight claim and returns/waits instead of racing a parallel run. Without a claim step, dedup catches only *sequential* repeats, not simultaneous ones.
- Today `severity`/`verdict`/`runbook` are hoisted onto `Investigation` *and* duplicated inside `report` — SIEM-isms in the envelope. Replacing them with a generic `outcome` (disposition + priority) that every domain maps onto enables **cross-domain listing** ("everything critical across SIEM *and* VM") without deserializing each report.

Two boundaries this decision draws:
- Dedup applies to the **formal triage path** (a filed alert/finding), not the **conversational MCP path** ("ask Benny about user Y"), which is exploratory and not persisted-and-deduped the same way. Idempotency is a property of a *module investigation*, not of every Benny interaction.
- Benny owns the "once" guarantee itself rather than pushing it upstream to the SIEM/scanner. With two entry points (API *and* MCP) and eventually multiple upstream callers, Benny is the only place the guarantee actually holds.

## Costing principle: the compression boundary

Every agentic loop re-sends its entire history on each turn, so a single agent's context cost grows ~quadratically with its tool-call turns. The lever for controlling cost is **where we put boundaries that absorb raw context and hand back something small** — not "more agents" or "fewer agents."

Decision ruleset for any unit of work:

```
  Unit of work                                   │ Compresses │ Needs     │ Build as
                                                  │ parent ctx?│ reasoning?│
  ─────────────────────────────────────────────  │ ────────── │ ───────── │ ──────────────────────
  Single call                                     │  no        │  no       │ inline tool
  N FIXED calls, FIXED summary rule               │  YES       │  no       │ composite deterministic tool
  N calls, path/verdict decided by a model        │  YES       │  yes      │ sub-agent (LLM loop)
  The investigation's own top-level reasoning     │  n/a       │  yes      │ the Analyst itself (never sharded)
```

Two rules that fall out and must not be violated:

1. **"Needs reasoning" ≠ "has a parameter."** `get_data(X, user=Y)` is only a sub-agent if a *model* must decide the control flow or synthesize a judgment. DataAgent qualifies because turning "failed logins for user Y" into a correct query against an unknown schema requires thinking *and* throws off scratch context (schema dumps, retries) we don't want in the Analyst. A parameterized-but-fixed query is still a composite tool.
2. **Do not shard the core reasoning.** The "given all findings, what's the verdict?" step is the Analyst's own job. Farming it out only moves the expensive context and adds a handoff.

Applied to Benny:

```
  DataAgent          sub-agent      (raw schema/rows/retries ≫ rows+notes returned)
  Identity/access    composite tool now  (fixed lookups → one IdentityAssessment);
                     graduate to IDPAgent only if the questions become reason-as-you-go
  Enrichment         composite tool or sub-agent depending on provider fan-out
  OrchestratorAgent  a cheap classify/route call — agentic only when the domain is ambiguous
  Analyst (per module) owns the reasoning — always an LLM, never sharded
```

Note Benny already does the mini-version: `lookup_user` fires two Okta SDK calls (user + manager) behind one tool and returns one `UserProfile` — a compression boundary with no LLM. The identity capability is that pattern grown up.

## Target project structure

Reorganize `src/` along the same horizontal/vertical seam, and pull transport concerns out of the package root.

```
src/
  core/                         # shared spine — domain-agnostic
    agents/
      base_agent.py             # BaseAgent (framework)
    orchestration/
      orchestrator.py           # OrchestratorAgent (routing)
      registry.py               # ModuleRegistry (generalized RunbookRegistry)
      module.py                 # AnalystModule contract / protocol

  capabilities/                 # HORIZONTAL — shared across modules
    data/
      base_data_agent.py
      sqlite_data_agent.py
      elastic_data_agent.py
    identity/
      okta.py                   # OktaClient
      assessment.py             # composite identity tool (→ IDPAgent later)
      user_profile.py           # UserProfile schema
    enrichment/                 # EnrichmentAgent + intel providers

  modules/                      # VERTICAL — one self-contained folder per domain
    siem/
      analyst.py                # SIEMAnalystAgent (was AnalystAgent)
      detection_engineer.py     # SIEM post-processing
      schemas.py                # Alert, IncidentReport (SIEM envelope)
      runbooks/                 # SIEM playbooks
    vuln_mgmt/                  # future module (same shape)
      analyst.py
      schemas.py
      runbooks/

  engines/                      # data backends (SQLite/ES/ClickHouse)
    base.py                     # QueryEngine ABC (also used by persistence)
    sqlite.py
    elasticsearch.py

  mcp/
    server/                     # Benny AS an MCP server (for external clients)
      app.py                    # FastMCP assembly (extracted from api/app.py)
      tools.py                  # was src/mcp_tools.py (list_runbooks, lookup_data, …)
      auth.py                   # was src/mcp_auth.py (BearerAuthMiddleware)
    clients/                    # Benny AS a client of external MCP servers
      clickhouse.py             # ClickHouse via MCP stdio (production data backend)
      # future: corporate-data MCPs

  api/                          # REST transport
    app.py                      # FastAPI factory (mounts mcp/server + routes)
    routes/
    schemas/

  config.py
  models.py                     # persistence (uses engines/)
  utils/
```

Rationale for the `mcp/` split (as requested):
- `mcp/server/` — everything about Benny *exposing* an MCP endpoint: the FastMCP app, tool registration, and bearer auth. This removes `mcp_auth.py`/`mcp_tools.py` from the package root and lifts the MCP assembly currently inline in `api/app.py` into one place.
- `mcp/clients/` — everything about Benny *consuming* external MCP servers. The CLAUDE.md already commits to ClickHouse via MCP stdio in production; future corporate-data MCPs land here too. An MCP-backed data source can then surface as a `capabilities/data` DataAgent whose engine speaks MCP — the two layers compose cleanly.

Placement notes / nuances:
- `engines/` stays near the top because `QueryEngine`/`SQLiteEngine` are shared between the data capability *and* the persistence layer (`models.py`). It is infrastructure, not a capability.
- The SIEM domain schemas (`Alert`, `IncidentReport`) live in `modules/siem/`; the `Investigation` record wrapper moves to `core/` as the idempotency envelope (see the investigation decision above).

## Migration path (slices)

Sequenced so the risky structural move lands first as a behavior-preserving refactor:

1. **Restructure + MCP move** — pure refactor: create `core/`, `capabilities/`, `modules/siem/`, `mcp/server/`, `mcp/clients/`; move files; keep behavior identical; tests green. No new abstractions yet.
2. **Module contract + registry + OrchestratorAgent** — introduce `AnalystModule`, `ModuleRegistry`, and the orchestrator; make SIEM the first module through the new contract.
3. **Identity capability** — extract `lookup_user` into a shared composite identity tool consumed by any module.
4. **VM module** — add `modules/vuln_mgmt/` end-to-end, exercising the contract with a genuinely different toolset.

## Design decisions

Resolved with the investigation-envelope decision above, these pin the architecture. Exact method signatures and edge cases are deferred to the per-slice delta specs.

1. **Orchestrator = router now, lead-analyst later.** `OrchestratorAgent` routes each request to exactly one module for MVP. Its return type is designed to also hold a *synthesized multi-module* answer, so cross-domain synthesis ("is this vulnerable asset also showing anomalous logins?") drops in later behind the same interface without a rewrite. Rationale: cross-domain synthesis is the endgame of the "chat with Benny" vision but not MVP; a pure router would be a dead end.

2. **One entry, two speeds — short-circuit inside the orchestrator.** A single seam `handle(request, hint=None)`: when the domain is explicit (API carries `alert.type`), the adapter passes a `hint` and routing dispatches directly with no LLM; when the entry is free-form (MCP chat), no hint is passed and the orchestrator LLM-classifies via each module's `accepts()`. One code path, two speeds — no duplicated dispatch logic across adapters.

3. **Module = typed `Protocol` + explicit registration.** A module implements the `AnalystModule` Protocol (sketch under "The module contract" above) and is added to the `ModuleRegistry` at startup. Chosen over directory+manifest and entry-point plugins because the codebase is small, strongly typed, and modules are core-authored — a Protocol keeps full static typing and matches the existing `BaseDataAgent`/`BaseAgent` style. Playbooks (runbooks) stay folder-based *inside* each module, giving drop-a-file ergonomics for playbooks without losing typing on the module wiring.

4. **Capabilities via a typed registry the module selects from.** Startup builds all capability instances centrally (backends are ops config — hosts, keys, index patterns, already in `config.py`) and passes a typed `Capabilities` object to `build_analyst(caps)`; each module picks the instances it consults (e.g. `caps.data["logs"]`). Chosen over static hand-wiring (which edits `create_app` per module) and a DI container (a mini-framework, premature). This matches the SIEM/VM insight: shared DataAgent *class*, different *instances/backends*, module chooses which.

5. **Identity = composite tool now, swappable to an agent.** Ship a composite `IdentityAssessment` tool, exposed to analysts as a *single capability call* whose internals can later become an `IDPAgent` without changing callers. Promote only when a follow-up lookup depends on a prior result *and* the output is a judgment rather than facts.

6. **MCP-backed data = a `QueryEngine` over the MCP client.** When Benny consumes an external MCP (ClickHouse in prod, future corp-data), it is wrapped as a `QueryEngine` implementation so `capabilities/data` treats native and MCP-backed sources uniformly. Keeps the capability model and `mcp/clients/` composed rather than special-cased.
