## ADDED Requirements

### Requirement: MCP server exposes lookup_data tool
The MCP server SHALL expose a `lookup_data` tool that accepts a natural-language `query` string, passes it to the configured data agent(s), and returns the result as a JSON string.

#### Scenario: Successful data lookup
- **WHEN** a client calls `lookup_data` with a natural-language query (e.g. "how many failed logins in the last hour?")
- **THEN** the server routes the query to the appropriate data agent, which uses its own LLM + tools to determine what to query, and returns the result as a JSON string

#### Scenario: Multiple data agents configured
- **WHEN** both a SQLite agent and an Elasticsearch agent are initialised
- **THEN** `lookup_data` routes to the agent whose `routing_description` best matches the query — the same routing logic used by AnalystAgent's `query_data` tool

#### Scenario: Lookup failure returns error string
- **WHEN** the data agent raises an unhandled exception
- **THEN** the tool returns a JSON object with an `error` key describing the failure rather than propagating the exception to the MCP transport layer

### Requirement: MCP server exposes list_runbooks tool
The MCP server SHALL expose a `list_runbooks` tool that returns the names and descriptions of all registered runbooks as a JSON array, so callers can discover what investigation types Benny supports.

#### Scenario: Runbooks are listed
- **WHEN** a client calls `list_runbooks`
- **THEN** the server returns a JSON array where each entry has `name` and `description` fields

### Requirement: MCP server initialises all configured data agents at startup
The MCP server SHALL share the data agents already initialised by the FastAPI lifespan — no separate initialization.

#### Scenario: Agents available immediately
- **WHEN** the FastAPI app has completed its lifespan startup
- **THEN** `lookup_data` tool calls can be served without any additional initialization

### Requirement: MCP server is mounted at /mcp in the existing FastAPI app
The MCP server SHALL be mounted as a Streamable HTTP sub-application within the existing FastAPI process, not as a separate entry point.

#### Scenario: Both interfaces available from one process
- **WHEN** `uv run python main.py` is executed
- **THEN** both the REST API routes and the `/mcp` endpoint are available on the same port
