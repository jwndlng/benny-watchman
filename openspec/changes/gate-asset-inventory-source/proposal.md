## Why

The composition root builds and `initialize()`s a SQLite DataAgent on the VM asset-inventory DB (`vuln.db`) **unconditionally** at startup — even when it is unconfigured and empty. This is the lone data source that ignores the project's "a source runs iff its config section is present" rule, and it directly violates `multi-datasource-routing`'s "SHALL NOT build an always-on default data source" clause. The result: every deployment (minimal, pure-env, and dev) must carry an otherwise-unused `vuln.db`, and startup depends on a file nobody asked for. Log sources (`[data.sqlite]`, `[data.elastic]`) are already correctly gated; the asset source is the exception.

## What Changes

- Make `[vuln]` optional: `Settings.vuln` becomes `VulnSettings | None = None` (present ⇒ enabled), matching `[kibana]`, `[okta]`, and `[data.elastic]`.
- The composition root builds the asset-inventory DataAgent and adds it to `Capabilities.data` **only when `[vuln]` is present**.
- `VulnModule` stays registered and `POST /findings` keeps working regardless; its `data_sources` reflect what is configured — **intel-only** when `[vuln]` is absent (mirrors SIEM with no configured log source, which runs with no log query tool). This is **not breaking** to the API surface.
- `config.toml.example`: comment out `[vuln]` to match the optional-section convention, with a note that enabling it requires seeding `vuln.db` via `tests/harness/seeder/asset_db.py`.
- Tests that exercise VM / `POST /findings` configure `[vuln]` explicitly.

## Capabilities

### New Capabilities

_(none)_

### Modified Capabilities

- `multi-datasource-routing`: the "configured data sources are authoritative / no always-on default data source" requirement explicitly covers the VM asset-inventory DataAgent — it is built iff `[vuln]` is present.
- `vuln-management-module`: the asset/vuln inventory data source is config-gated; when `[vuln]` is absent the VM module remains registered and routable but runs intel-only (no asset query tool).

## Impact

- **Code:** `src/config.py` (`Settings.vuln` optionality), `src/adapters/api/app.py` (gate the asset-agent build; derive `VulnModule.data_sources` from what is configured), `config.toml.example`.
- **Behavior:** minimal/pure-env boots no longer require `vuln.db`; VM without `[vuln]` degrades to intel-only instead of forcing an empty always-on database.
- **Tests:** VM/findings tests and `tests/conftest.py` fixtures must supply `[vuln]`.
- **No** dependency changes, no API-route changes, no MCP tool-surface changes.
