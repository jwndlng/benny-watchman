## 1. Dependencies

- [x] 1.1 Add `mcp` to `pyproject.toml` dependencies and run `uv lock`

## 2. Bearer Token Auth

- [x] 2.1 Add `MCP_BEARER_TOKEN` to `src/config.py` — read from env var, leave as `None` if unset
- [x] 2.2 In `app.py` lifespan startup: if `MCP_BEARER_TOKEN` is not set, generate with `secrets.token_urlsafe(32)`, store on config/app state, and print the token to stdout with instructions to add it to `.env`
- [x] 2.3 Create a FastAPI dependency `require_mcp_token` that validates `Authorization: Bearer <token>` against the resolved token; returns 401 on mismatch

## 3. MCP Tools Module

- [x] 3.1 Create `src/mcp_tools.py` with a `register_tools(mcp, data_agents, registry)` function that defines and registers both tools on the given `FastMCP` instance
- [x] 3.2 `list_runbooks()` returns a JSON array of `{name, description}` from the registry
- [x] 3.3 `lookup_data(query: str)` routes to the best-matching data agent using the same routing logic as `AnalystAgent.query_data`, runs the query, and returns JSON; catches exceptions and returns `{"error": ...}`

## 4. Wire into FastAPI

- [x] 4.1 In `app.py`, instantiate `FastMCP("benny")` and call `register_tools(mcp, data_agents, registry)` inside the lifespan after data agents are initialised
- [x] 4.2 Mount `mcp.streamable_http_app()` at `/mcp` on the FastAPI app, wired with the `require_mcp_token` dependency

## 5. Tests

- [x] 5.1 Unit test bearer token resolution in `tests/unittests/test_mcp_auth.py` — verify env var takes precedence, generated token is non-empty, 401 on wrong token
- [x] 5.2 Unit test `register_tools` in `tests/unittests/test_mcp_tools.py` — mock data agents and registry, verify `list_runbooks` output shape and `lookup_data` happy path + exception handling

## 6. Documentation

- [x] 6.1 Add `MCP_BEARER_TOKEN` to `.env.example` with a comment explaining the generate-on-first-run behaviour
- [x] 6.2 Add Claude Code `mcpServers` registration snippet to `CLAUDE.md` under a new "MCP Server" section, including the `headers` auth field
