## Why

Benny runs as a REST API today, which requires curl or a custom client to invoke. Exposing Benny as a local MCP server lets Claude Code and the Antigravity CLI call it directly as a tool — no context-switching, no terminal, just "investigate this alert" in the chat.

## What Changes

- New `mcp_server.py` entry point using the `mcp` Python SDK with stdio transport
- Two MCP tools exposed: `investigate_alert` and `list_runbooks`
- Shared agent initialization logic extracted so both `app.py` and `mcp_server.py` use the same setup path
- `mcp` added to dependencies in `pyproject.toml`

## Capabilities

### New Capabilities

- `mcp-server`: stdio MCP server entry point that exposes Benny's investigation capability as MCP tools, with startup initialization of all configured data agents

### Modified Capabilities

<!-- none — existing agent and engine behaviour is unchanged -->

## Impact

- **New file**: `mcp_server.py` (project root, sibling of `main.py`)
- **Modified**: `pyproject.toml` — add `mcp` dependency
- **Modified**: `src/api/app.py` — extract shared agent initialization into a reusable helper so `mcp_server.py` can call the same setup without duplicating it
- **No changes** to existing agents, engines, runbooks, or REST API behaviour
