# AI SOC Analyst (Security Hero)

## Project Overview
An autonomous AI agent that performs Tier 2/3 Security Analyst work. It receives alerts via REST API, investigates them using an agentic reasoning loop (ReAct pattern) with Clickhouse log data via MCP, and returns structured triage reports. Fully unattended, 24/7 operation.

## Tech Stack
- **Language:** Python
- **API:** Flask (or similar lightweight framework)
- **Data:** Clickhouse via MCP (stdio transport)
- **LLM:** Model-agnostic (Anthropic, Google, OpenAI) — configurable at runtime
- **Container:** Docker
- **Logging:** Structured JSON to stdout, collected by Vector daemonset

## Key Design Decisions
- Agent is **investigation-only** — it never triggers remediation actions
- Skills are **progressively loaded** — only metadata at init, full content on demand
- DB permissions enforced at **Clickhouse user level**, not query parsing
- Web access restricted to a **repo-managed allowlist**
- All repo changes (skills, context, allowlist) trigger a **new Docker build**
- Guardrails: max iterations + max token budget per investigation

## Key Files
- `pm/DESIGN.md` — Full architecture and requirements specification
- `pm/AGENT_DESIGN.md` — Concrete agent design, flows, and PydanticAI implementation
- `pm/MILESTONES.md` — Project stages from skeleton to full PoC
- `pm/TODO.md` — Open design questions to resolve
- `runbooks/` — Runbook definitions (YAML frontmatter + Markdown)
