# MILESTONES.md: Project Stages

**MVP = Stage 5** — full pipeline with real data, enrichment, and a test harness.

---

## Stage 1 — Flask API

Define and expose the REST API contract before building any agent logic.

- [ ] OpenAPI specification
- [ ] `POST /investigate` — submit an alert, returns Incident Report
- [ ] `GET /investigations/{id}` — retrieve a past investigation
- [ ] `GET /runbooks` — list available Runbooks
- [ ] Stub responses (no agent logic yet)

**Exit criteria:** API is fully specified and returns stub responses. Spec can be used to generate clients or register a CLI Skill.

---

## Stage 2 — Orchestration

Introduce the OrchestratorAgent and a dummy AnalystAgent to prove routing works.

- [ ] OrchestratorAgent with one tool per Runbook
- [ ] First Runbook definition (e.g., `brute-force-triage`)
- [ ] Dummy AnalystAgent: responds with a hardcoded Incident Report without investigating
- [ ] Fallback: if no Runbook matches, a default AnalystAgent is bootstrapped
- [ ] CI check: validate no two Runbooks have overlapping capability scope

**Exit criteria:** Alerts route to the correct Runbook. The dummy AnalystAgent returns a plausible response. Fallback path works.

---

## Stage 3 — AnalystAgent + DataAgent

Replace the dummy AnalystAgent with a real investigation loop backed by live data.

- [ ] DataAgent with live Clickhouse connection (`list_tables`, `get_schema`, `get_sample`, `run_query`)
- [ ] AnalystAgent dynamically bootstrapped by OrchestratorAgent (system prompt + scoped tool set from Runbook)
- [ ] AnalystAgent delegates data requests to DataAgent in natural language
- [ ] Demo data / dev Clickhouse instance for local development
- [ ] Guardrails: max tool calls + token budget per investigation

**Exit criteria:** A real alert is submitted, the AnalystAgent investigates using live Clickhouse data, and returns a structured Incident Report.

---

## Stage 4 — External Enrichment

Introduce the EnrichmentAgent and give the AnalystAgent access to external threat intelligence via delegation.

- [ ] EnrichmentAgent with VirusTotal integration (IP, domain, hash lookups)
- [ ] Web lookup with repo-managed allowlist
- [ ] IDP lookup (user identity, roles, account status)
- [ ] AnalystAgent delegates enrichment requests to EnrichmentAgent via `enrichment_request()`
- [ ] Enrichment tools declared and scoped per Runbook in YAML frontmatter

**Exit criteria:** AnalystAgent can enrich findings with external threat intel and identity data during an investigation, routed through the EnrichmentAgent.

---

## Stage 5 — Testing Harness (MVP)

Validate quality and enable iteration on Runbooks and prompts.

- [ ] Golden dataset: known alerts with human-verified verdicts
- [ ] LLM-as-judge evaluation (reasoning accuracy, data precision, final verdict)
- [ ] Multi-model benchmarking (run same dataset against different LLMs)

**Exit criteria:** Quality is measurable. Different models can be compared against the same scenarios.

---

## Post-MVP Features

The following are out of scope for the MVP/PoC and will be implemented as separate features:

### ReviewerAgent
A skeptical critic that re-examines AnalystAgent findings before producing the final Incident Report. Adds a double-check pass and detection rule improvement suggestions. See `AGENT_DESIGN.md` for full spec.

### DetectionEngineerAgent
Takes the completed Incident Report and drafts optimized detection rules — tuning thresholds, reducing false positives, or rewriting logic based on investigation findings. Triggered automatically for false positive verdicts or where rule improvement suggestions are present.

### ThreatHunterAgent + MCP Server
Enables interactive, ad-hoc investigations from a human analyst via GenAI CLI (Claude Code, Gemini CLI). The ThreatHunterAgent turns unstructured observations into hypotheses and hands them to the AnalystAgent. Requires an MCP server for persistent session support.

### Response Agent
Structured action recommendations that can evolve into semi-automated response execution.

### Regression Testing & CI
Full Golden Dataset runs on every change to Runbooks or context files.

### Investigation Context Persistence (Re-investigation Loop)
Each investigation stores its full context (findings, tool call history, intermediate conclusions). The ReviewerAgent or a human analyst can critique specific findings via the Router, which re-triggers the AnalystAgent with the original context + feedback. This enables iterative investigations rather than single-pass analyses.

### Agent Learning Persistence (Cross-investigation Memory)
Each agent running a ReAct loop persists notable observations from its investigation — e.g., "in loop 3, correlated source IP with known staging host." When the same alert pattern fires again, the agent loads prior learnings as additional context, enabling it to shortcut to relevant hypotheses faster over time. Stored per alert signature in the data lake.
