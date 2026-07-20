## 1. Dependency & scaffolding

- [x] 1.1 Promote `pydantic-settings` to an explicit dependency in `pyproject.toml` (pin ~=2.13) and sync the lockfile
- [x] 1.2 Add `config.toml` to `.gitignore`
- [x] 1.3 Create `config.toml.example` with all non-secret sections (`[agent]`, `[persistence]`, `[data.sqlite]`, `[data.elastic]`, `[kibana]`, `[vuln]`) and today's default values — no secrets. **DEVIATION: `[logging]` dropped — logging stays env-driven (`LOG_LEVEL`/`LOG_FORMAT`/`LOGFIRE_TOKEN`, the latter a secret) since observability bootstraps outside `config`; adding an unwired `[logging]` would reintroduce the dead-setting anti-pattern this change removes.**
- [x] 1.4 Trim `.env.example` to secrets + local overrides only (`AGENT_MODEL_API_KEY`, `KIBANA_TRIAGE_API_KEY`, `ELASTIC_API_KEY`, `OKTA_CLIENT_ID`, `OKTA_PRIVATE_KEY`, `MCP_BEARER_TOKEN`, optional `CONFIG_FILE`)

## 2. Settings models (`src/config.py`)

- [x] 2.1 Define nested section models (`AgentSettings`, `PersistenceSettings`, `SqliteDataSettings`, `ElasticDataSettings`, `DataSettings` with optional `sqlite`/`elastic`, `KibanaSettings`, `OktaSettings`, `VulnSettings`) with `Field(description=...)` and types. **DEVIATION: no `McpSettings`/`LoggingSettings` — `mcp_bearer_token` is a single top-level env-only field; logging dropped (see 1.3).**
- [x] 2.2 Define `Settings(BaseSettings)` composing the sections; add `SettingsConfigDict(toml_file=...)` reading `CONFIG_FILE` or default `config.toml`
- [x] 2.3 Implement `settings_customise_sources` → precedence `init > env > dotenv > TomlConfigSettingsSource > defaults`
- [x] 2.4 Inject each secret from its canonical flat env var, preserving names; keep secrets out of the example. **DEVIATION: `validation_alias` does NOT work for this — smoke-tested and falsified: pydantic-settings resolves a nested field's alias as a key *inside* the section table, not as a top-level env var. Implemented via a `model_validator(mode="before")` (`_inject_secrets`) that stamps env secrets into their sections; a present section missing its secret still fails fast.**
- [x] 2.5 Keep `set_model_api_key()` behavior (map `agent.api_key` → provider SDK env var) working against the new model
- [x] 2.6 Expose a module-level `settings`/`config` instance (fail-fast on validation error), replacing the old `config` object

## 3. Composition root (`src/api/app.py`)

- [x] 3.1 Build log DataAgents from config: one per present `[data.*]` section (SQLite iff `data.sqlite`, Elastic iff `data.elastic`) — remove the always-on SQLite agent
- [x] 3.2 Build the vuln asset DataAgent from `[vuln]`; build persistence from `[persistence]`
- [x] 3.3 Select the triage platform from `[kibana]` presence (already the pattern) via the new settings; pass `url` (may include `/s/<space-id>`), `case_owner`, and env-sourced api key
- [x] 3.4 Remove all remaining `DATA_BACKEND_ENGINE` references and the dead `engine` field

## 4. Docs

- [x] 4.1 Update `AGENT.md` configuration section: TOML-canonical, env-for-secrets, `config.toml.example` → `config.toml`, `[data.*]` enablement, Kibana space in the URL

## 5. Tests

- [x] 5.1 Update `tests/conftest.py` for the new nested `data.sqlite` shape. **DEVIATION: kept the lightweight duck-type `_Config` for the `client` fixture (fully deterministic, no TOML/env leakage from a dev's local `config.toml`); the real `Settings` load path is exercised by `test_config.py` instead.**
- [x] 5.2 Add tests for precedence (env > TOML > default), secret injection from env, and missing-`config.toml` fallback (`tests/unittests/test_config.py`)
- [x] 5.3 Add config-level tests for data-source selection: section presence enables `sqlite`/`elastic`, absence → `None`. **NOTE: covered at the config-model layer (section→optional model) + the existing sqlite route path + `_select_triage_platform` test; full app-level all-four-combo boot not exhaustively re-tested (needs heavy dual-agent init mocking).**
- [x] 5.4 Add a test that a `/s/<space-id>` Kibana url yields space-prefixed API paths (httpx join)
- [x] 5.5 Update/remove any test asserting old env-var config behavior; run the full unit suite green

## 6. Verify

- [x] 6.1 Boot the app with a sample `config.toml` (env for secrets) and confirm `check_platform_access` / startup logs show the intended data sources + platform
