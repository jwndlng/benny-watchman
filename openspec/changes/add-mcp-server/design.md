## Context

Benny's investigation pipeline lives in `Orchestrator`, which is initialised once in `app.py`'s lifespan and stored on `app.state`. A second interface (MCP) can be mounted into the same FastAPI process and share that orchestrator instance — no separate process, no duplicated startup cost.

The `mcp` Python SDK provides `FastMCP`, which exposes a `streamable_http_app()` that can be mounted as a FastAPI sub-application on any path. Tools are registered as async functions that close over the orchestrator.

## Goals / Non-Goals

**Goals:**
- Expose `lookup_data` and `list_runbooks` as MCP tools on `/mcp` in the existing FastAPI app
- Share the same data agents and registry across REST and MCP interfaces
- Bearer token auth on the `/mcp` mount — generated at startup or stable via env var
- Support multiple simultaneous clients (engineers, CLI sessions) over HTTP
- Single process to start and manage

**Non-Goals:**
- stdio transport — Streamable HTTP replaces it entirely
- A separate `mcp_server.py` entry point
- Extracting `build_orchestrator` from `app.py` — the lifespan already owns initialization; MCP tools just close over the shared state
- Okta JWT auth in this change — deferred to a follow-up once multi-engineer network deployment is needed

## Decisions

### Streamable HTTP transport, not stdio

stdio requires Claude Code to spawn a subprocess per session and pass env vars explicitly. Streamable HTTP lets multiple clients connect to an already-running Benny instance — matching the model where `uv run python main.py` is the one thing you start, and both REST and MCP just work.

**Alternative considered**: stdio in a separate `mcp_server.py`. Rejected — two processes means two Elasticsearch initializations, separate logs, and env var duplication in every client config.

### Bearer token auth with generate-on-first-run UX

The `/mcp` mount requires `Authorization: Bearer <token>` on every request. The token is resolved at startup:

1. If `MCP_BEARER_TOKEN` is set in the environment — use it (stable across restarts)
2. If not set — generate with `secrets.token_urlsafe(32)` and print to stdout:
   ```
   MCP Bearer Token: <token>
   Add to .env as MCP_BEARER_TOKEN=<token> to make it permanent.
   ```

This means the first run self-documents: copy the printed token into `.env` and your Claude Code config, and it never changes again. No manual token management for local dev.

**Production path**: swap the FastAPI dependency for Okta JWT validation — same mount point, same tools, different auth backend. Deferred to a follow-up change.

**Alternative considered**: no auth, bind to `127.0.0.1` only. Rejected — the multi-engineer use case requires network exposure, and generating a token at startup costs nothing.

### Mount `FastMCP` into the existing `app.py`

`FastMCP("benny").streamable_http_app()` returns an ASGI app that FastAPI can mount at `/mcp`. Tools are registered on the `FastMCP` instance; the instance is created once and tools close over the data agents and registry captured during lifespan.

### Tools defined as closures inside lifespan

Data agents aren't available at import time — they're constructed during lifespan. Tools are therefore registered as closures inside the lifespan function, capturing the live references. This avoids module-level state and keeps the dependency explicit.

### Claude Code config uses `url` + `headers`

```json
{
  "mcpServers": {
    "benny": {
      "url": "http://localhost:8000/mcp",
      "headers": { "Authorization": "Bearer <token>" }
    }
  }
}
```

## Risks / Trade-offs

- **Server must be running**: Unlike stdio, Claude Code can't auto-spawn Benny. If the server isn't up, the MCP tool calls fail immediately. → Acceptable for a tool you're actively running.
- **No streaming progress**: MCP tool calls are request/response. `lookup_data` can take several seconds depending on the query. → Document in the tool description.
- **Concurrent lookups**: Multiple clients can call `lookup_data` simultaneously. PydanticAI agents are stateless per-run so each call gets its own agent run context — safe.

## Open Questions

- None — scope is well-defined.

## Future Direction

Once this is in place, the Orchestrator is the natural evolution point: making it a full conversational agent (where runbook routing is a tool/skill rather than a hard dispatch step) would make the MCP interface genuinely chat-capable rather than one-shot. The HTTP transport and shared state laid down here are the right foundation for that. Okta JWT auth is the natural upgrade path once Benny moves to a shared network deployment.
