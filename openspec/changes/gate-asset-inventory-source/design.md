## Context

Log data sources are config-authoritative: the composition root ([src/adapters/api/app.py](../../../src/adapters/api/app.py)) builds a `SQLiteDataAgent`/`ElasticDataAgent` only when `[data.sqlite]`/`[data.elastic]` is present, and `Settings.data.sqlite`/`.elastic` are `… | None = None`. The VM asset-inventory source is the exception: `Settings.vuln` is `VulnSettings = VulnSettings()` (always defaulted, so always "present"), and `app.py` unconditionally constructs an asset `SQLiteDataAgent` on `cfg.vuln.db_path` (`vuln.db`), `await`s `initialize()`, adds it to `Capabilities.data`, and registers `VulnModule(data_sources=[cfg.vuln.name])`.

Consequences today: a fresh checkout carries an empty `vuln.db` that is opened and introspected at every boot; pure-env and minimal deployments must ship a file they never populate; and the behaviour contradicts `multi-datasource-routing`'s "SHALL NOT build an always-on default data source." The asset DB does have a real purpose and a seeder ([tests/harness/seeder/asset_db.py](../../../tests/harness/seeder/asset_db.py)) — it is simply wired as always-on rather than opt-in.

## Goals / Non-Goals

**Goals:**
- Make the VM asset-inventory DataAgent config-gated, exactly like the log sources — built iff `[vuln]` is present.
- Keep `VulnModule` registered and `POST /findings` working whether or not `[vuln]` is configured.
- Bring `[vuln]` in line with the other optional sections in config, model, and `config.toml.example`.

**Non-Goals:**
- Merging, relocating, or consolidating any database files (the "one SQLite for all" idea is explicitly rejected — evidence sources and Benny's own state stay separate).
- Populating/seeding `vuln.db`, or adding a unified seed entrypoint (separate concern).
- Any change to the SIEM path, the log sources, persistence, or the MCP/REST surface.
- Implementing the `scalyr_db` loader or the Elastic asset path.

## Decisions

### 1. `Settings.vuln` becomes optional (`VulnSettings | None = None`)
Mirror `kibana`/`okta`/`data.elastic`. "Present ⇒ enabled" is the established convention; a defaulted section can never express "off." The `_inject_secrets` validator does not reference `vuln` (the section has no secret), so optionality is safe there. `config.toml.example` comments out `[vuln]` to match the other opt-in sections, with a one-line note that enabling it requires seeding `vuln.db` via `tests/harness/seeder/asset_db.py`.

_Alternative considered:_ keep `[vuln]` defaulted but add a `vuln.enabled` bool. Rejected — introduces a second, inconsistent enablement idiom when the codebase already uses section-presence everywhere.

### 2. Gate only the asset agent; keep `VulnModule` registered (intel-only when absent)
When `[vuln]` is absent, do **not** build the asset agent and do **not** add it to `Capabilities.data`; still register `VulnModule`, with `data_sources = [cfg.vuln.name] if cfg.vuln else []`. `VulnModule.investigate` already filters unknown source names (`[caps.data[n] for n in self._data_sources if n in caps.data]`), so an empty list yields an analyst with the intel tool but no asset query tool — a valid degraded mode (CVE/EPSS/KEV reasoning without inventory context).

This mirrors SIEM, which stays registered with whatever log sources exist (`multi-datasource-routing`: "No configured log source → the analyst is given no log query tool"), and preserves the `POST /findings` contract.

_Alternative considered:_ gate the whole `VulnModule` registration on `[vuln]`. Rejected — it conflates "asset inventory is configured" with "VM triage is available," and would turn `POST /findings` into a not-found when `[vuln]` is omitted, a breaking API change. The asset DB is a *data source*, not the module's on/off switch.

### 3. Scope the spec change to the two capabilities that actually assert the rule
`multi-datasource-routing` owns "no always-on default data source"; `vuln-management-module` owns "the VM analyst consults an asset/vuln inventory via a DataAgent from `Capabilities.data`." Both need the gating clause; nothing else does. `runtime-configuration` is untouched (its requirements are about TOML/env/precedence/secrets, not per-section enablement).

## Risks / Trade-offs

- **Silent capability drop:** a deployment that forgets `[vuln]` gets intel-only VM without an obvious error. → The startup log already lists the data sources it built; VM running without an asset source is visible there, and is the same failure mode SIEM already has for missing log sources. Documented in `config.toml.example`.
- **Test breakage:** existing VM / `POST /findings` tests assume the always-on asset agent. → Part of the change: those tests (and `tests/conftest.py` fixtures) explicitly configure `[vuln]`; the full suite must stay green.
- **Example now boots VM off by default:** copying `config.toml.example` no longer enables VM. → Intended (opt-in like the other sections); the commented block + seeding note make enabling it a two-step, documented action.

## Migration Plan

Pure code/config change, no data migration. Deploy is a normal Docker rebuild. Deployments that rely on VM asset lookups must add a `[vuln]` section (previously implicit) and ensure `vuln.db` is seeded — call this out in the release notes. Rollback: revert the commit; the always-on behaviour returns.

## Open Questions

_None._ The module-registration knock-on (Decision 2) is settled: keep `VulnModule` registered, intel-only when `[vuln]` is absent.
