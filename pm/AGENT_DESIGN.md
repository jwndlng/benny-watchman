# AGENT_DESIGN.md: Concrete Agent Architecture

## Framework

The agent system is built on **PydanticAI**, providing structured, typed tool calls and model-agnostic LLM integration.

## Design Philosophy

The multi-agent design is not just about task decomposition — **each agent operates with a fundamentally different system prompt and cognitive role**. The same LLM, given a different system prompt, behaves differently. This is the core value:

| Agent | System Prompt Mindset |
|-------|----------------------|
| OrchestratorAgent | "You are a triage router. Your only job is to match this alert to the right Runbook." |
| AnalystAgent | "You are a thorough investigator. Gather all relevant evidence before drawing conclusions." |
| DataAgent | "You are a database expert. Translate data requests into optimal queries for the connected backend." |
| EnrichmentAgent | "You are a threat intelligence specialist. Enrich indicators with external context — reputation, attribution, and threat actor data." |
| ReviewerAgent | "You are a skeptical critic. Challenge the findings. Is the evidence sufficient? What could be wrong?" |
| ThreatHunterAgent | "You are a proactive hunter. Turn unstructured observations and hypotheses into structured investigations." |
| DetectionEngineerAgent | "You are a detection rule expert. Given investigation findings, improve or rewrite detection rules to reduce noise and increase fidelity." |

Separating these roles prevents a single agent from being simultaneously investigator and judge — a known failure mode where LLMs tend to confirm their own earlier reasoning.

---

## End-to-End Pipeline

1. **Receive Alert** — Flask API ingests the alert and passes it to the OrchestratorAgent.
2. **Investigate** — AnalystAgent performs an in-depth investigation using all tools available in the selected Runbook.
3. **Double Check** — ReviewerAgent critically re-examines the findings: is the verdict supported by evidence? Could it be a false positive?
4. **Write Report** — ReviewerAgent produces an Incident Report with response suggestions and detection rule improvement recommendations.
5. **Close the Loop** — Result is written back to `ai_alerts_table` and the Incident Report is returned to the caller.

---

## Agent Roles

### OrchestratorAgent (Triage)

- **Purpose:** Receives the incoming alert and determines which Runbook applies.
- **Tools:** One tool per Runbook — each tool returns the full Runbook content (system instructions + available tools for the AnalystAgent).
- **Output:** Bootstraps the AnalystAgent with the selected Runbook.
- **Does not investigate** — its only job is routing.

### AnalystAgent (Investigator)

- **Purpose:** Performs an in-depth investigation autonomously using all tools available in the Runbook.
- **Configuration:** Dynamically bootstrapped by the OrchestratorAgent — system prompt and available tools come from the selected Runbook.
- **Tools:** External enrichment services (VirusTotal, IDP, web lookups) + `data_request` to delegate data retrieval to the DataAgent.
- **Loop:** Iterates over data requests and enrichment lookups, evaluating after each one whether the data is sufficient to conclude. Continues until confident or the max lookup depth is reached.
- **Guardrail:** Maximum of **10 tool calls** per investigation.
- **Output:** Structured findings summary passed to the ReviewerAgent.

### DataAgent (Query Expert)

- **Purpose:** Receives natural language data requests from the AnalystAgent and translates them into optimized queries against the configured backend.
- **Abstraction:** The AnalystAgent never writes queries — it describes what it needs (e.g., "all logins for user X in the last hour"). The DataAgent handles schema discovery, query construction, and execution.
- **Backend-agnostic:** Supports multiple backends (Clickhouse, Elasticsearch, etc.). The AnalystAgent is unaware of which backend is in use.
- **Tools:** `list_tables`, `get_schema`, `get_sample`, `run_query` — all data access tools live here, not on the AnalystAgent.
- **Output:** Structured query results returned to the AnalystAgent.

#### DataAgent Evolution Path

The current design uses a single `DataAgent` backed by one data source. As the system scales, there are two possible evolution paths — both are valid, neither needs to be decided now:

**Option A — Generic DataAgent orchestrator**
A front-facing `DataAgent` that runs its own ReAct loop to find the right data across multiple backends. `AnalystAgent` asks "get me auth logs for this user", and `DataAgent` figures out which backend holds that data, queries it, and returns results. Requires DataAgent to maintain a catalog of what data lives where.

**Option B — Merged multi-backend DataAgent**
One `DataAgent` with tools from all backends registered simultaneously. Simpler wiring, but context window grows with every added backend and unrelated tools become noise.

**Current approach (PoC):** `DataAgent` base class + `DataSQLiteAgent` subclass. Subclasses own their connection lifecycle and register backend-specific tools as closures. Adding Clickhouse = `DataClickhouseAgent(DataAgent)`. AnalystAgent only depends on the base `DataAgent` type.

### EnrichmentAgent (Threat Intelligence) — *Stage 4 (MVP)*

- **Purpose:** Enriches indicators of compromise (IPs, domains, hashes, URLs) with external threat intelligence.
- **Invoked by:** AnalystAgent via a natural language enrichment request (e.g., "check reputation of IP 1.2.3.4").
- **Tools:** VirusTotal, IDP lookup, web lookup (pre-authorized allowlist).
- **Design:** Isolates all external API calls in one agent. Adding a new threat intel provider means adding a tool here — no changes to other agents.
- **Output:** Structured enrichment result returned to the AnalystAgent.

### ReviewerAgent (Critic + Reporter) — *Post-MVP*

- **Purpose:** Critically re-examines the AnalystAgent's findings, then produces the final Incident Report.
- **Double Check:** Applies a skeptical lens — does the evidence actually support the verdict? Are there alternative explanations? Could this be a false positive?
- **No data lookups** — it reasons over the provided findings only, it does not call tools.
- **Report:** Produces the Incident Report including response suggestions and detection rule improvement recommendations.
- **Close the Loop:** Writes the result back to `ai_alerts_table` to mark the alert as processed.
- **Output:** A structured Incident Report returned to the caller.

### ThreatHunterAgent (Interactive Investigator) — *Post-MVP*

- **Purpose:** Enables ad-hoc, interactive threat hunting sessions initiated by a human analyst via GenAI CLI (Claude Code, Gemini CLI).
- **Mode:** Conversational — receives unstructured observations or hypotheses from the analyst and translates them into structured investigations delegated to the AnalystAgent.
- **Session:** Persistent MCP session (not stateless REST) — required for multi-turn back-and-forth with the analyst.
- **Output:** Investigation findings streamed back to the analyst in the CLI session.

### DetectionEngineerAgent (Rule Optimizer) — *Post-MVP*

- **Purpose:** Takes a completed Incident Report and drafts optimized detection rules — tuning thresholds, reducing false positives, or rewriting logic based on the investigation findings.
- **Invoked by:** Triggered after the ReviewerAgent produces the Incident Report, particularly for false positive verdicts or where rule improvement suggestions are present.
- **No data lookups** — reasons over the Incident Report and the original detection rule only.
- **Output:** A draft detection rule change (diff or full rule) with an explanation of what was changed and why.

---

## Investigation Flow

```
Caller (SIEM)
     │
     │  POST /investigate  { alert }
     ▼
┌─────────────────────────────┐
│         Flask API           │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐   Step 1: Receive & Route
│      OrchestratorAgent      │
│                             │
│  - runbook_brute_force()    │
│  - runbook_phishing()       │
│  - runbook_data_exfil()     │
│  - ...                      │
│                             │
│  → Selects matching Runbook │
└─────────────┬───────────────┘
              │  Runbook (system prompt + tool list)
              ▼
┌─────────────────────────────┐   Step 2: Investigate
│       AnalystAgent          │
│                             │
│  Configured by Runbook:     │
│  - System instructions      │
│  - Scoped tool set          │
│                             │
│  Data sufficiency loop:     │
│  "I need data X"            │
│    → DataAgent              │◄──────────────────────┐
│  Enough data?               │                       │
│    No  → next request       │   ┌───────────────────┴─────┐
│    Yes → conclude           │   │       DataAgent          │
│  (max 10 tool calls)        │   │                         │
└─────────────┬───────────────┘   │  - Schema discovery     │
              │  delegate ───────►│  - Query construction   │
              │  ◄── results ─────│  - Backend execution    │
              │                   └─────────────────────────┘
              │  Findings summary
              ▼
┌─────────────────────────────┐   Steps 3–5: Review, Report & Close
│       ReviewerAgent         │
│                             │
│  3. Double check findings   │
│     (skeptical re-review)   │
│  4. Write Incident Report   │
│     - Response suggestions  │
│     - Rule improvements     │
│  5. Write to ai_alerts_table│
└─────────────┬───────────────┘
              │  Incident Report
              ▼
           Caller
```

---

## Runbook Structure

Each Runbook is a file in `runbooks/` with YAML frontmatter and Markdown instructions:

```yaml
---
name: brute-force-triage
description: Investigates potential brute force and credential stuffing attacks
tools:
  - clickhouse_query
  - clickhouse_schema
  - web_lookup
---
```

The Markdown body becomes the AnalystAgent's system prompt for the investigation.

The OrchestratorAgent exposes each Runbook as a tool. When called, the tool returns the full Runbook content, which bootstraps the AnalystAgent.

---

## Available Tools by Agent

### AnalystAgent Tools

The AnalystAgent focuses on *what* to investigate, not *how* to retrieve data or enrich indicators. Its tools are:

| Tool | Description |
|------|-------------|
| `data_request(description)` | Delegate a natural language data request to the DataAgent |
| `enrichment_request(indicator, type)` | Delegate an enrichment lookup to the EnrichmentAgent |

### EnrichmentAgent Tools

The EnrichmentAgent owns all external threat intelligence lookups. Adding a new intel provider means adding a tool here only.

| Tool | Description |
|------|-------------|
| `virustotal_lookup(indicator)` | Check IP, domain, or hash reputation against VirusTotal |
| `idp_lookup(user_id)` | Look up user identity, roles, and account status |
| `web_lookup(url)` | Fetch a pre-authorized URL for threat intel research |

### DataAgent Tools

The DataAgent owns all data access. It handles schema discovery, query construction, and execution against the configured backend.

| Tool | Description |
|------|-------------|
| `list_tables(database)` | List available tables and descriptions |
| `get_schema(table)` | Get columns and data types for a table |
| `get_sample(table, n=5)` | Get n sample rows to understand data shape |
| `run_query(sql)` | Execute an arbitrary query against the backend |

Adding a new backend (e.g., Elasticsearch) means adding new DataAgent tools — no changes to any other agent.

---

## Incident Report Schema

The ReviewerAgent produces a structured JSON report returned to the caller:

```json
{
  "alert_id": "string",
  "severity": "critical | high | medium | low | informational",
  "verdict": "true_positive | false_positive | inconclusive",
  "confidence": 0.0,
  "summary": "string",
  "findings": ["string"],
  "recommended_actions": ["string"],
  "detection_rule_improvements": ["string"],
  "runbook": "string",
  "investigation_truncated": false
}
```

- `recommended_actions` — human-readable response suggestions only, nothing is executed.
- `detection_rule_improvements` — suggestions to improve the originating SIEM detection rule (e.g., reduce false positives, tighten thresholds).
- `investigation_truncated` — `true` if the max tool call guardrail was hit before a confident conclusion.

> **Future:** `recommended_actions` may evolve into structured action objects when semi-automated response is introduced.

---

## Fallback Handling

If the OrchestratorAgent cannot match any Runbook with sufficient confidence:
- Return a structured response to the caller indicating no applicable Runbook was found.
- Include the alert details and a suggested action (e.g., manual review).
- Do **not** fall back to a generic investigation — an unscoped AnalystAgent is unpredictable.

---

## Open Questions

- [ ] Should the OrchestratorAgent use a single LLM call (classifier) or a full reasoning step to select a Runbook? A classifier is cheaper and more predictable.
- [ ] Can multiple Runbooks apply to the same alert? If so, do we run AnalystAgents in parallel or pick the best match?
- [ ] Should IDP lookups live on the AnalystAgent (direct API call) or be routed through the DataAgent if IDP data is stored in the data lake?
