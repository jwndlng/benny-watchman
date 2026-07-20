## 1. Config model

- [ ] 1.1 In `src/config.py`, change `Settings.vuln` from `VulnSettings = VulnSettings()` to `VulnSettings | None = None` (present ⇒ enabled), matching `kibana`/`okta`. Leave `VulnSettings` and its `db_path`/`name` defaults unchanged.
- [ ] 1.2 Confirm `_inject_secrets` requires no change (`VulnSettings` has no secret) — no edit expected; verify no other code reads `config.vuln` unconditionally outside the composition root.

## 2. Composition root (`src/adapters/api/app.py`)

- [ ] 2.1 Build the asset `SQLiteDataAgent`, `await initialize()`, and include it in `all_agents` / `Capabilities.data` **only when `cfg.vuln is not None`**.
- [ ] 2.2 Register `VulnModule` regardless of `[vuln]`, deriving `data_sources = [cfg.vuln.name] if cfg.vuln else []` so it runs intel-only when the section is absent — `POST /findings` behavior unchanged.
- [ ] 2.3 Confirm the MCP `register(all_agents, …)` call receives the asset agent only when present (it reads the same `all_agents` list — no extra change beyond 2.1).

## 3. Example config

- [ ] 3.1 In `config.toml.example`, comment out the `[vuln]` section (matching `[data.elastic]`/`[kibana]`/`[okta]`), adding a one-line note that enabling it requires seeding `vuln.db` via `tests/harness/seeder/asset_db.py`.

## 4. Tests

- [ ] 4.1 `tests/unittests/test_config.py`: assert `[vuln]` present ⇒ `settings.vuln` is a `VulnSettings`; absent ⇒ `settings.vuln is None`.
- [ ] 4.2 App-level test: with `cfg.vuln = None`, no asset agent is built and `Capabilities.data` has no `asset_inventory` entry, while `VulnModule` is still registered.
- [ ] 4.3 Test that `POST /findings` still routes to `VulnModule` when `[vuln]` is absent (intel-only path; analyst built with no asset query tool).
- [ ] 4.4 Keep the existing `client` fixture green (it sets `vuln` present); update any test that assumed the always-on asset agent.
- [ ] 4.5 Run the full unit + e2e suite (`tests/e2e/test_vuln_triage.py` included); confirm green.

## 5. Verify

- [ ] 5.1 Boot the app with a `config.toml` that omits `[vuln]`; confirm startup logs list only the configured sources, `vuln.db` is not created/opened, and `POST /findings` returns a triage.
- [ ] 5.2 Boot with `[vuln]` present (seeded `vuln.db`); confirm the asset agent initializes and the VM analyst has the `asset_inventory` query tool.
