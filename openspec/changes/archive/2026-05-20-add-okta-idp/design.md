## Context

`AnalystAgent.lookup_user()` currently returns a hardcoded stub for all usernames. The `UserProfile` model already defines the right shape — name, email, team, role, manager, employment status, tenure, location, access level. The only missing piece is a real data source.

Okta's Users API (`/api/v1/users/{login}`) returns almost all of these fields in one call, with a second call needed for the manager. The integration is intentionally narrow: read-only, single-user lookups, synchronous, no caching.

## Goals / Non-Goals

**Goals:**
- `OktaClient` fetches real user identity from Okta and maps it to `UserProfile`
- `lookup_user` in `AnalystAgent` delegates to `OktaClient` when Okta is configured
- Graceful fallback to the existing stub when Okta is unconfigured or the user is not found
- No behavior change for environments without Okta credentials

**Non-Goals:**
- `on_call` and `out_of_office` fields — not available in Okta; always `False` for now
- Caching or batching — one lookup per `lookup_user` call, no shared state
- Group membership or factor/MFA status queries
- Writing to Okta or any non-read operation

## Decisions

### 1. `httpx` for HTTP, synchronous call

`lookup_user` is a synchronous tool method on `AnalystAgent` (registered via `tool_plain`, not `tool`). PydanticAI calls it synchronously during the agent loop. Switching to async would require migrating to `tool` with an `AgentContext`, which is a larger change.

`httpx` supports both sync and async and is already a transitive dependency in the stack. Using `httpx.Client` (sync) keeps the implementation simple and consistent with the existing synchronous tool pattern. If the tool is later migrated to async, swapping `httpx.Client` for `httpx.AsyncClient` is a one-line change.

`requests` was also considered but `httpx` is preferred for its typing and modern API.

### 2. `OktaClient` as a plain class, not a PydanticAI agent

This is a thin REST wrapper, not an AI agent. There is no reasoning loop, no tool registration, and no LLM involved. A simple class with one public method (`get_user`) keeps the boundary clear and the code testable without mocking PydanticAI.

### 3. Optional wiring — `OktaClient | None` injected into `AnalystAgent`

`AnalystAgent` accepts an optional `okta_client: OktaClient | None = None` parameter. When `None`, `lookup_user` returns the existing stub. When set, it delegates to `OktaClient.get_user()`.

The `Orchestrator` constructs `OktaClient` from config if `OKTA_ORG_URL` and `OKTA_API_TOKEN` are present, otherwise passes `None`. This keeps the opt-in behaviour at the wiring layer, not buried in `OktaClient`.

Alternative considered: check `config.okta` inside `lookup_user` directly. Rejected because it couples `AnalystAgent` to config and makes the dependency invisible — injection is more testable and explicit.

### 4. Field mapping from Okta API response

| `UserProfile` field | Okta source |
|---|---|
| `name` | `profile.firstName + " " + profile.lastName` |
| `email` | `profile.email` |
| `team` | `profile.department` (empty string → `"unknown"`) |
| `role` | `profile.title` (empty string → `"unknown"`) |
| `manager` | `profile.displayName` from manager endpoint, or `"unknown"` |
| `employment_status` | mapped from `status`: `ACTIVE`→`"active"`, `DEPROVISIONED`→`"terminated"`, others→`"on_leave"` |
| `start_date` | `activated` field (ISO 8601 date), fallback `2000-01-01` if absent |
| `tenure_days` | `(today - start_date).days` |
| `work_location` | `profile.city` or `"remote"` if absent |
| `timezone` | `profile.timezone` or `"UTC"` if absent |
| `access_level` | `profile.userType` or `"unknown"` if absent |
| `on_call` | `False` (not in Okta) |
| `out_of_office` | `False` (not in Okta) |
| `termination_date` | `None` (not reliably available in Okta) |

### 5. Error handling — stub on failure, not raise

If Okta returns 404 (user not found), or any HTTP/network error occurs, `OktaClient.get_user()` returns `None`. `lookup_user` then falls back to the stub. Investigations are not aborted due to an identity lookup failure — the analyst continues with `"unknown"` context and notes the limitation in its output.

## Risks / Trade-offs

**Okta rate limits** — Okta's `/api/v1/users` endpoint is rate-limited (typically 600 req/min on Okta developer, higher on production). One `lookup_user` call makes 2 HTTP requests (user + manager). For typical investigation volumes this is not an issue. → No mitigation needed now; add caching if rate limit errors appear in production.

**Synchronous HTTP in async context** — The FastAPI app is async, but `lookup_user` is called synchronously inside the PydanticAI agent loop which itself is called via `run_sync`. Running synchronous `httpx` from within a sync context inside an async app is safe as long as it is not called from the async event loop thread directly. The current `investigate()` call chain uses `run_sync` which blocks the event loop thread; this is pre-existing behaviour, not introduced here. → Accept for now; tracking in the broader async migration consideration.

**API token in environment** — `OKTA_API_TOKEN` is a long-lived SSWS token. It must be treated as a secret and injected via environment variable, not committed. → Standard secret management; no code change needed.

## Migration Plan

1. Create `src/integrations/__init__.py` and `src/integrations/okta.py`
2. Add `OktaConfig` to `src/config.py`
3. Update `AnalystAgent.__init__` to accept `okta_client: OktaClient | None = None`
4. Update `Orchestrator.__init__` to construct and inject `OktaClient` when configured
5. Update `create_app()` lifespan to pass `OktaClient` (if configured) to `Orchestrator`
6. No rollback needed — unconfigured environments are unaffected

## Open Questions

- Should `work_location` map from `profile.city`, `profile.countryCode`, both, or a custom Okta attribute? Depends on how your Okta org populates these fields. Default to `profile.city` for now.
- Should `access_level` map from `profile.userType` or a custom Okta attribute (e.g. a group membership)? Custom attributes are org-specific; `userType` is the safest default.
