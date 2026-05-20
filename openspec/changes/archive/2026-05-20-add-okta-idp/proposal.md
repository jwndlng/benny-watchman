## Why

The `lookup_user` tool in `AnalystAgent` returns a hardcoded stub. Without real identity context — employment status, role, department, manager, tenure — the analyst cannot assess whether observed activity is expected for a given user. Connecting to Okta gives the analyst the identity signal it needs to distinguish legitimate access from compromised accounts or insider threats.

## What Changes

- `OktaClient` added at `src/integrations/okta.py`:
  - `get_user(login: str) -> UserProfile` calls Okta Users API (`GET /api/v1/users/{login}`) and manager API (`GET /api/v1/users/{id}/manager`)
  - Maps Okta fields to existing `UserProfile` model (name, email, team/department, role/title, manager, employment_status, start_date, tenure_days, work_location, timezone)
  - Fields not available in Okta (`on_call`, `out_of_office`) default to `False` — can be extended later via PagerDuty / calendar integrations
  - Returns stub `UserProfile` if user not found (graceful degradation — investigation continues)
- `AnalystAgent.lookup_user()` wired to `OktaClient` when `OKTA_ORG_URL` and `OKTA_API_TOKEN` are configured; falls back to current stub behavior if unconfigured
- Config additions: `OKTA_ORG_URL`, `OKTA_API_TOKEN`

## Capabilities

### New Capabilities
- `okta-idp-integration`: Real identity and employment context for investigated users via Okta

### Modified Capabilities
- None — `UserProfile` model shape unchanged; stub fallback preserved for environments without Okta

## Impact

- `src/integrations/okta.py` — new file
- `src/agents/analyst_agent.py` — `lookup_user()` delegates to `OktaClient`
- `src/config.py` — new `OktaConfig` with org URL and API token
- Requires `httpx` or `aiohttp` for async HTTP calls (or use `requests` if sync is acceptable)
- No changes to API, schemas, or persistence
- Can be implemented independently of `refactor-multi-datasource-foundation`
