## Why

During DataAgent initialization, `get_sample()` returns real log events — real usernames, IP addresses, and internal hostnames — which get embedded in the routing description and sent to the LLM API on every investigation. This is an unnecessary data exposure risk, especially in regulated environments where PII and internal infrastructure details should not leave the perimeter via API calls.

## What Changes

- DataAgent `initialize()` applies a configurable masking pass to sample events before building the routing description
- Sensitive fields (usernames, email addresses, IP addresses, hostnames) are replaced with realistic-looking synthetic placeholders that preserve type and format (e.g. `user.name: "john.doe"` → `user.name: "[user]"`, `source.ip: "10.0.1.5"` → `source.ip: "[ip]"`)
- Field patterns to mask are configurable (allowlist of safe fields, or denylist of sensitive ones) — defaults cover common ECS fields
- Masking applies only to the routing description (sent to AnalystAgent / LLM); raw data returned from `run_query()` during investigations is unaffected
- No LLM call needed — pure field-pattern matching and value replacement

## Capabilities

### New Capabilities
- `routing-description-privacy`: Masking of PII and sensitive values in DataAgent routing descriptions before LLM injection

### Modified Capabilities
- None

## Impact

- `BaseDataAgent.initialize()` — masking applied after sampling, before formatting routing description
- `src/engines/` — no changes; `get_sample()` remains unmasked (raw data for query use)
- New config: `DATA_AGENT_MASK_FIELDS` (list of field name patterns) with sensible ECS defaults
- No API changes, no schema changes, no breaking changes
