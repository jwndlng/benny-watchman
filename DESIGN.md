# DESIGN.md: AI Supported Security Analyst (Security Hero)

## 1. Vision & Core Concept

The **Security Hero** is an autonomous AI agent designed to perform the work of a Tier 2/3 Security Analyst. It operates as a **Reasoning Engine** that dynamically pulls in specialized "Skills" and interacts with on-premise infrastructure (Clickhouse) via the **Model Context Protocol (MCP)** to investigate alerts. The model operates within an **Agentic Workflow**, meaning it doesn't just answer questions—it plans, executes tools, and evaluates its own findings before reporting.

## 2. Technical Architecture

The system is written in **Python** and uses a **Hybrid-Cloud** approach. The LLM remains in the cloud, while the execution runtime and data access layers reside in a private network via a Dockerized container.

### Key Components:

* **Orchestrator (The Brain):** A model-agnostic reasoning engine. It manages the state of the investigation and decides which tools to invoke. The underlying LLM is configurable at runtime (see R5).
* **Agent Skills Registry:** A modular repository of expertise (`Skills/` folder) following the **2026 Agent Skills Specification**.
* **Local MCP Server:** A Python-based bridge using the **Model Context Protocol** to communicate with on-premise Clickhouse logs via `stdio` transport.
* **REST API:** A lightweight Python web framework (e.g., Flask) serving as the entry point for SIEM alerts (e.g., from Splunk or Sentinel), returning structured triage reports.

### Autonomous Operation

The agent operates **fully unattended** — it receives an alert, autonomously iterates through its reasoning loop (loading skills, querying data, evaluating findings), and returns a final triage report without human intervention. This enables **24/7 coverage**, including overnight and weekends, where no analyst is online. Each investigation is self-contained; if the agent fails mid-investigation, the alert must be re-submitted by the caller.

### Execution Environment (Docker)

We use a **Dockerized application** to ensure immutability and version control.

* **Lifecycle:** Any update to a `SKILL.md` or the `CONTEXT.md` necessitates a new Docker build. This allows for seamless rollbacks and ensures the AI's "knowledge base" is always in sync with the code.
* **Environment Variables:** Credentials for Clickhouse and API keys for Anthropic/Google are injected at runtime. The MCP server pulls these directly from the container environment.
* **Networking:** The container is placed in a network segment that can reach the Clickhouse nodes but has no inbound access from the public internet.

---

## 3. Requirement Specifications

### R1: Dynamic Skill Loading (Progressive Disclosure)

* **Mechanism:** The agent is initialized only with the metadata (name/description) of available skills.
* **Autonomy:** The agent must autonomously call the `load_skill` tool to retrieve the full content of a `SKILL.md` only when necessary. This saves tokens and prevents "prompt distraction."
* **Standard:** Skills follow the 2026 Spec: YAML frontmatter for metadata + Markdown for instructions.
* **No Overlap:** Each skill must have a distinct, non-overlapping responsibility. A CI workflow validates that no two skills share the same capability scope by checking their metadata.

### R2: On-Premise Data Connectivity (MCP)

* **Transport:** Uses **Stdio transport**. The orchestrator starts the MCP server as a subprocess.
* **Permissions:** Enforced at the **Clickhouse user level**. The agent's database user has read-only access to all log tables. The sole exception is a dedicated `ai_alerts_table`, where the agent can update alerts tagged for AI review.
* **Optimized Access:** The agent is instructed to use Clickhouse-specific functions (e.g., `uniqCombined` for counts) via the `clickhouse-sql` skill.

### R3: Controlled Web Research

* **Boundary:** Web access is restricted to a set of pre-authorized security URLs defined in an allowlist file in the repository.
* **Safety:** The `web_search` tool uses this allowlist to filter requests. This prevents the agent from visiting potentially malicious sites that could attempt a "Prompt Injection" attack.
* **Lifecycle:** Any change to the allowlist requires a commit and triggers a new Docker build, following the same immutability principle as skills.

### R4: Pre-Authorization & Permissions

* **Implicit Trust:** The agent is pre-authorized for all investigative tasks (querying data, loading skills, web lookups). It does not pause to ask for permission.
* **No Outbound Actions:** The agent is strictly investigative — it returns a triage report but never triggers remediation actions (e.g., blocking users, firewall rules). Any downstream action based on the report is out of scope.

### R5: Model-Agnostic Orchestration & Benchmarking

* **Abstraction Layer:** The orchestrator communicates with LLMs through a unified interface that abstracts provider-specific APIs (e.g., Anthropic, Google, OpenAI).
* **Runtime Configuration:** The model is selected via configuration (environment variable or API parameter), not hardcoded. Swapping models requires zero code changes.
* **Benchmarking:** The test harness (Section 6) can run the same Golden Dataset against multiple models and produce comparative scoring across reasoning accuracy, data precision, and final verdict.

---

## 4. MCP Server & Tool Definitions

The `mcp_clickhouse.py` server exposes the following functions to the Orchestrator. The design philosophy is: **discovery tools** help the agent understand the data landscape, while `run_query` gives it full freedom to write arbitrary investigative queries.

### Discovery Tools

* **`list_tables(database)`**: Returns a list of tables and their descriptions to help the AI plan its query.
* **`get_schema(table)`**: Returns the exact columns and data types for a table.
* **`get_sample_data(table, n=5)`**: Returns `n` sample rows from a table, allowing the agent to quickly understand the shape and content of the data.

### Investigative Tool

* **`run_query(sql)`**: Executes an arbitrary SQL query and returns the result as a JSON array. This is the agent's primary tool for investigation — it is not restricted to predefined query patterns.
  * *Constraint:* Automatically appends `LIMIT 500` if no limit is specified, to prevent memory issues.

### Error Handling

* All tools return structured error responses (e.g., query syntax errors, timeouts, connection failures) so the agent can reason about the failure and adjust its approach.



---

## 5. Operation Loop (ReAct Pattern)

The agent follows a **Reason-Act-Observe** loop:

1. **Ingest:** API receives an alert.
2. **Reason:** Agent determines it needs the `brute-force-triage` skill and Clickhouse logs.
3. **Act:** Calls `load_skill` $\rightarrow$ Calls `run_query`.
4. **Observe:** Analyzes the log results. If inconclusive, it repeats step 3 with a different query or skill.
5. **Conclude:** Synthesizes the final "Security Rating" and "Recommended Actions."

### Guardrails

* **Max Iterations:** A configurable limit on the number of Reason-Act-Observe cycles. If exceeded, the agent must return its best findings so far with a note that the investigation was truncated.
* **Max Tokens:** A configurable token budget for the entire investigation. The orchestrator tracks cumulative token usage and forces a conclusion before the budget is exhausted.

### Observability

* **Logging:** The full investigation transcript (reasoning steps, tool calls, query results, errors) is logged as structured JSON to **stdout**. A Vector daemonset collects these logs and feeds them back into the data lake for audit trails and debugging.

---

## 6. Testing & Evaluation (LLM-as-a-Judge)

To ensure the **Security Hero** remains reliable, we use a **Test Harness** with a **Golden Dataset**.

### The Testing Workflow:

1. **Scenario Injection:** A fresh container is spun up and fed a "Golden Alert" (a known, verified attack from the past).
2. **Investigation:** The agent performs its full agentic workflow against a sanitized test-version of the Clickhouse datalake.
3. **Judging:** After the agent finishes, a **Judge Model** (e.g., Claude 4.5 Opus) evaluates the entire transcript.
* **Reasoning Accuracy:** Did it use the right skills?
* **Data Precision:** Did it write efficient SQL?
* **Final Verdict:** Does its rating match the human-verified "Ground Truth"?
4. **Scoring:** Success/Failure metrics are used to "tweak" the `CONTEXT.md` or the `Skills/` playbooks.
