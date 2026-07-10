## Why

The MCP server's bearer token auth is sufficient for solo local use but doesn't scale to a shared team deployment — there's no per-engineer identity, no token rotation, and no integration with existing access controls. Okta is already wired into Benny for the REST API, making it the natural upgrade path for MCP auth when multiple engineers need access.

## What Changes

- MCP auth strategy becomes configurable: `bearer` (current behaviour, default) or `okta` (JWT validation via existing `OktaClient`)
- When `okta` mode is active, the `require_mcp_token` FastAPI dependency validates the incoming JWT against Okta rather than comparing a static token
- New `MCP_AUTH_MODE` env var controls which strategy is active (`bearer` | `okta`)
- Bearer token behaviour is unchanged when `MCP_AUTH_MODE=bearer` — no breaking change for local dev setups

## Capabilities

### New Capabilities

- `mcp-okta-auth`: Okta JWT validation as an alternative auth backend for the `/mcp` mount, selectable via `MCP_AUTH_MODE`

### Modified Capabilities

- `mcp-server`: auth strategy on the `/mcp` mount becomes configurable — ADDED `MCP_AUTH_MODE` config and pluggable dependency

## Impact

- **Modified**: `src/config.py` — add `MCP_AUTH_MODE` config field
- **Modified**: `src/mcp_tools.py` (or wherever `require_mcp_token` lives) — swap static comparison for Okta JWT validation when mode is `okta`
- **Modified**: `.env.example` — document `MCP_AUTH_MODE`
- **No changes** to existing Okta integration, REST API auth, or bearer token local dev flow
- **Depends on**: `add-mcp-server` change being implemented first
