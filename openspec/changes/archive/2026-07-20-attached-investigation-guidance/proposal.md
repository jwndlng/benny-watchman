## Why

A real security analyst does not carry a copy of every runbook — they read the investigation guidance that ships with the alert, and only look deeper when it is thin. Benny does the opposite today: it maintains a repo of per-alert-type runbook files, matches one at dispatch, and injects it as the analyst's persona. In practice that repo is nearly empty (SIEM ships only `generic`, vuln ships `generic` + one barely-differentiated RCE file), the match key for Elastic is a free-text rule name that almost never matches a file, and — worst of all — the detection engineer's own investigation guide (the Elastic rule `note`) is fetched, then discarded. Benny throws away the guidance the SIEM already authored and falls back to a generic prompt.

## What Changes

- **The analyst's general METHOD becomes a stable, Benny-owned prompt** baked into the module/analyst base — no longer sourced from a `generic.md` runbook file. This is the trusted, reviewed, in-repo persona ("how a SOC analyst / vuln triager investigates").
- **Investigation guidance travels attached to each work item**, as a new structured field on the input contract (`Alert` / `Finding`). Two producers, one field:
  - **PUSH** intake (authenticated API/MCP submitters) supplies guidance in the payload.
  - **PULL** intake (`TriagePlatform`) populates it **eagerly** at fetch time. For Elastic, the platform reads the detection rule's investigation `note`, cached per-rule (reusing the existing `self._rule` cache). This keeps the analyst on the correct side of the `platforms → core` boundary — no lazy analyst-triggered pull, no dependency inversion.
- **Trust seam made explicit.** The guidance field is treated as trusted GUIDANCE (authored by the security team / a trusted authenticated submitter); raw event data in the payload stays EVIDENCE and MUST never steer the investigation. The general method states this so an attacker-controlled string in `raw` cannot redirect the loop.
- **Observability hook.** Guidance presence + length is logged per triaged item, so detection-note coverage/quality becomes a dashboard question rather than a guess.
- **BREAKING: the `RunbookRegistry` and per-type runbook files are removed.** `.match(type)` dispatch, the `src/modules/*/runbooks/` directories, and the `generic.md` files all go away. No repo-override escape hatch is kept (YAGNI — re-addable later if note coverage proves poor).
- **`Alert.type` / `Finding.type` demote to metadata + dedup key** — they no longer drive runbook selection.
- **`Investigation.runbook` field is repurposed as guidance provenance** (was it present, from what source) rather than the name of a matched runbook.
- **The `list_runbooks` MCP tool is repurposed to module/alert-type discovery** ("what can Benny investigate") — with no runbook repo, listing runbooks is incoherent.

## Capabilities

### New Capabilities
- `investigation-guidance`: the structured guidance type attached to work items, the two-producer (push payload / pull-platform-eager) population model, the guidance-vs-evidence trust seam, and the guidance-provenance observability hook.

### Modified Capabilities
- `analyst-module-contract`: rewrite the "Runbook selection remains internal to the module" requirement — the analyst's general method lives in the module and guidance rides on the input; neither is exposed through the `AnalystModule` contract (the contract shape is unchanged).
- `elastic-triage-platform`: `type` mapping no longer "drives runbook matching" (it becomes plain metadata); add a requirement that the platform populates the `Alert` guidance field from the rule investigation `note`, cached per-rule.
- `vuln-management-module`: `Finding.type` becomes metadata/dedup only (drop "used for runbook matching"); remove the internal runbook-selection requirement.
- `agent-orchestration`: the `POST /investigate` scenario asserting `Investigation.runbook` matches the alert type/`generic` changes — the field now records guidance provenance.
- `project-structure`: drop the `src/modules/*/runbooks/` directories and `RunbookRegistry` from the layout; update the MCP scenario for the repurposed `list_runbooks` tool.

## Impact

- **Removed:** `src/core/orchestration/runbook_registry.py`; `src/modules/siem/runbooks/`; `src/modules/vuln_mgmt/runbooks/`; `RunbookRegistry` wiring at the composition root (`src/api/app.py`).
- **Modified contracts:** `src/modules/siem/alert.py`, `src/modules/vuln_mgmt/finding.py` (new guidance field); `src/schemas/investigation.py` (`runbook` → provenance).
- **Modified analysts/modules:** `src/modules/siem/{module,analyst}.py`, `src/modules/vuln_mgmt/{module,analyst}.py` — general method as baked-in `instructions`, guidance surfaced in the user turn.
- **Modified platforms:** `src/platforms/base.py` (guidance is part of the produced item), `src/platforms/elastic.py` (rule-note fetch + cache), `src/platforms/memory.py` (pass-through guidance).
- **Modified surfaces:** `src/api/routes/runbooks.py` and the MCP `list_runbooks` tool → module/alert-type discovery.
- **Tests:** route tests asserting `Investigation.runbook`, runbook-matching tests, and platform intake-mapping tests all need updating.
