## Why

Benny's configuration is a flat wall of environment variables assembled by hand in `src/config.py`, which mixes three things that should be separate: **secrets** (API keys, tokens), **structured settings** (models, paths, hosts, limits), and **dead knobs**. That last category bit us in prod: `DATA_BACKEND_ENGINE` is read into config but consumed nowhere, the SQLite log DataAgent is built unconditionally, and the Elastic one is added only when `ELASTIC_*` is set — so "which data source runs" is not actually configurable, and you can silently end up with an empty SQLite agent *and* Elastic both registered. Env-only config also has no natural place for structure (a Kibana space, a list of data sources) and no schema/validation.

A canonical, typed TOML config — with secrets injected via env — makes configuration structured, validated, and authoritative ("whatever is configured is what runs"), while keeping the safe `.env`-for-secrets story.

## What Changes

- **TOML becomes the canonical config source.** A git-ignored `config.toml` holds all non-secret settings; a committed `config.toml.example` is copied to `config.toml` (mirroring the existing `.env.example` → `.env` flow). `.gitignore` updated.
- **`src/config.py` is rewritten on `pydantic-settings`** (already installed 2.13.1 via a transitive dep — promoted to an explicit dependency). Typed `BaseSettings` models load from `TomlConfigSettingsSource` + env, with `settings_customise_sources` giving precedence **env > TOML > defaults**. `tomllib` is stdlib on 3.14.
- **Secrets stay in env, only:** `AGENT_MODEL_API_KEY`, `KIBANA_TRIAGE_API_KEY`, `ELASTIC_API_KEY`, `OKTA_CLIENT_ID`, `OKTA_PRIVATE_KEY`, `MCP_BEARER_TOKEN`. Non-secret settings move to TOML: agent model + `max_requests`/`max_data_requests`, persistence engine/path, data-source config, kibana url/case_owner, elastic host/index_pattern, okta domain, vuln db_path/name, log level.
- **Data sources become config-authoritative** via `[data.elastic]` / `[data.sqlite]` sections — a section's presence enables that source. **BREAKING:** removes the dead `DATA_BACKEND_ENGINE` selector and the always-on SQLite agent; the composition root selects log DataAgents from config. One of each for now; the section shape leaves room for more later.
- **Kibana config can express a space** — the base URL may include `/s/<space-id>` (fixes the recent prod finding where Benny queried the default space instead of `isec`).
- **Docs + tests updated** — `AGENT.md` config section, `.env.example` trimmed to secrets + local overrides, `tests/conftest.py` mock config aligned to the new settings shape.

## Capabilities

### New Capabilities
- `runtime-configuration`: TOML-canonical, typed configuration loaded via `pydantic-settings`; env-for-secrets with `env > TOML > defaults` precedence; the `config.toml.example` → `config.toml` convention; validation at startup.

### Modified Capabilities
- `multi-datasource-routing`: the configured data source(s) are authoritative — a source runs iff its config section is present — replacing the always-on SQLite agent and the ignored `DATA_BACKEND_ENGINE` selector.
- `elastic-triage-platform`: Kibana configuration may target a non-default space via a `/s/<space-id>` URL prefix.

## Impact

- **Config core:** `src/config.py` rewritten as `pydantic-settings` models (biggest change).
- **Composition root:** `src/api/app.py` selects log DataAgents from config sections instead of always-SQLite + conditional-Elastic.
- **New files:** `config.toml.example`; **modified:** `.gitignore` (ignore `config.toml`), `.env.example` (trim to secrets + local overrides), `pyproject.toml` (explicit `pydantic-settings` dep).
- **Docs:** `AGENT.md` configuration section.
- **Tests:** `tests/conftest.py` mock config → construct real settings from an inline TOML/env fixture (or an updated stub); any test asserting old env-var behavior.
- **Operational (BREAKING):** deployments must provide a `config.toml` (or rely on env overrides for every value); `DATA_BACKEND_ENGINE` is removed; enabling a data source now means adding its `[data.*]` section.
