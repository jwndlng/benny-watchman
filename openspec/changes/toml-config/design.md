## Context

`src/config.py` is a set of plain classes reading `os.environ.get(...)` at import time, assembled by hand. It conflates secrets, structured settings, and dead knobs (`DATA_BACKEND_ENGINE` is read but never consumed; the SQLite log agent is always built in `src/api/app.py` while Elastic is added only when `ELASTIC_*` is set). There is no schema, no validation, and no natural place for structure (a Kibana space, a list of data sources). `pydantic-settings` (2.13.1) is already installed transitively and ships `TomlConfigSettingsSource`; `tomllib` is stdlib on 3.14. This change makes TOML the canonical, typed config with env reserved for secrets/overrides.

## Goals / Non-Goals

**Goals:**
- One canonical, typed, validated config: TOML for structure, env for secrets + local overrides, precedence **env > TOML > defaults**.
- Configuration is authoritative — a data source runs iff its config section is present; no dead selectors, no always-on agent.
- `config.toml.example` → `config.toml` convention mirroring `.env.example` → `.env`.
- Kibana config can target a non-default space.
- Fail fast at startup on invalid/missing-required config.

**Non-Goals:**
- Multiple sources of one kind (several SQLite/Elastic) — the section shape allows it later; not built now.
- Secret management beyond env (no vault integration).
- Hot-reload of config at runtime.
- Changing persistence/query-engine internals — only where they read config.

## Decisions

### 1. `pydantic-settings` with a customised source order
`Settings(BaseSettings)` composed of nested section models (`agent`, `persistence`, `data`, `kibana`, `elastic`, `okta`, `mcp`, `logging`). `settings_customise_sources` returns, highest priority first:

```
init_settings  >  env_settings  >  dotenv_settings  >  TomlConfigSettingsSource(cls)  >  defaults
```

So env always wins over TOML (secrets + local overrides), TOML over defaults. Promote `pydantic-settings` to an explicit `pyproject.toml` dependency. *Alternative considered:* roll our own `tomllib` + env overlay — rejected; reimplements precedence/validation that pydantic-settings already gives us, and the codebase is Pydantic-native.

### 2. Secrets live in env, cohesively — injected by a before-validator
Secret fields stay *inside* their section (e.g. `kibana.api_key`) so sections are cohesive, and each is sourced from its existing flat env var, preserving current names and never appearing in `config.toml.example`:

> **Correction (implementation):** the originally-planned `validation_alias` approach was **smoke-tested and falsified** — pydantic-settings resolves a *nested* field's alias as a key *inside* the section table (`kibana.KIBANA_TRIAGE_API_KEY`), not as a top-level env var, so the flat secret never merged. Implemented instead with a `model_validator(mode="before")` (`_inject_secrets`) that stamps each canonical env secret into its section dict. A present-but-secretless section still fails fast.


| Field | env var (alias) |
|---|---|
| `agent.api_key` | `AGENT_MODEL_API_KEY` |
| `kibana.api_key` | `KIBANA_TRIAGE_API_KEY` |
| `elastic.api_key` | `ELASTIC_API_KEY` |
| `okta.client_id` / `okta.private_key` | `OKTA_CLIENT_ID` / `OKTA_PRIVATE_KEY` |
| `mcp.bearer_token` | `MCP_BEARER_TOKEN` |

Because env > TOML, a secret accidentally placed in TOML is still overridden by env, and it's kept out of the example so the convention holds. *Alternative considered:* a separate env-only `Secrets` class — rejected; it splits `kibana.url` (TOML) from `kibana.api_key` (env) across two objects and complicates wiring.

### 3. TOML schema — sections, presence enables
```toml
[agent]
model = "google-gla:gemini-3.1-flash-lite-preview"
max_requests = 15
max_data_requests = 10

[persistence]
engine = "sqlite"
db_path = "investigations.db"

[data.sqlite]              # present ⇒ SQLite log source enabled
name = "security_logs"
db_path = "data.db"

[data.elastic]             # present ⇒ Elastic log source enabled
name = "elasticsearch"
host = "https://es-host:9200"
index_pattern = "logs-*"

[kibana]                   # present ⇒ Elastic triage platform; absent ⇒ in-memory
url = "https://…/s/isec"   # space expressed in the URL
case_owner = "securitySolution"

[vuln]
db_path = "vuln.db"
name = "asset_inventory"

[logging]
level = "INFO"
```
`data.sqlite` / `data.elastic` are `Optional` nested models; the composition root builds a log DataAgent for each present section. This replaces always-on SQLite + the dead `DATA_BACKEND_ENGINE`. *Note:* API keys for these sections still come from env aliases, not the TOML block.

### 4. Kibana space via the URL
No separate `space` field — the `/s/<space-id>` prefix rides in `kibana.url` (verified: httpx joins `base_url=".../s/isec"` + `/api/...` → `.../s/isec/api/...`). Simplest, and matches the prod finding. A dedicated `space` field is a possible later nicety (see Open Questions).

### 5. `config.toml` discovery and optionality
`TomlConfigSettingsSource` reads `config.toml` from the repo/CWD root; path overridable via a `CONFIG_FILE` env var. If absent, settings fall back to env + defaults, so pure-env deployments and tests still work. Required-but-unset fields raise a Pydantic `ValidationError` at construction → startup aborts with a clear message.

### 6. Tests build settings in-process
`tests/conftest.py` stops hand-rolling a `_Config` duck-type and instead constructs the real `Settings(...)` with explicit overrides (or points `CONFIG_FILE` at a tmp TOML). This keeps tests exercising the real validation path.

## Risks / Trade-offs

- **BREAKING: deployments need a `config.toml` (or full env).** → Ship `config.toml.example` with today's defaults; because env overrides everything, an all-env deployment still works with zero TOML.
- **Secret-in-TOML footgun** → kept out of the example, documented as env-only, and env precedence means it can't silently take effect over the intended env value; optional follow-up: warn if a known-secret key appears in TOML.
- **Import-time singleton churn** → today `config` is a module-level instance; a validation error now fails at import/startup. That's the intended fail-fast, but tests must construct `Settings` explicitly rather than import a pre-built global.
- **Overlap with the unarchived `attached-investigation-guidance` change** (both touch `elastic-triage-platform`) → this change modifies the *Platform-selection* requirement, that one modifies the *alert-mapping* requirement; disjoint, but archive order should be watched.

## Migration Plan

1. Promote `pydantic-settings` to an explicit dep. 2. Rewrite `src/config.py` as `Settings` + nested models. 3. Add `config.toml.example`, gitignore `config.toml`, trim `.env.example` to secrets + overrides. 4. Update `src/api/app.py` to select data sources / platform from config sections. 5. Update `tests/conftest.py` + any env-var-asserting tests. Rollback = revert; no data migration (config is not runtime state).

## Open Questions

- Should `config.toml` path default to repo root or an XDG-style location? (Lean: repo root + `CONFIG_FILE` override.)
- Keep `persistence.engine` as a field when SQLite is the only implementation today, or drop until ClickHouse lands? (Lean: keep — it's a real forward-looking axis, unlike `DATA_BACKEND_ENGINE`.)
- Dedicated `kibana.space` field vs. URL-embedded `/s/<id>`? (Lean: URL for now.)
