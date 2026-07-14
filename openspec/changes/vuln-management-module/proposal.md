## Why

Vulnerability Management triage is the second triage domain and the real test of the module contract. It is structurally the same shape as SIEM alert triage — investigate an input against playbooks + corporate context, reach a verdict — but with almost entirely different tooling: asset/vuln *state* data and heavy external enrichment (CVE, EPSS, KEV) instead of high-volume time-series logs. If adding VM is "drop in a module," the modular architecture has succeeded.

## What Changes

- **A `vuln_mgmt` vertical module** implementing the `AnalystModule` contract end-to-end:
  - **Input contract:** a `Finding` (CVE, asset, CVSS)
  - **Playbooks:** runbooks matched by vulnerability class, folder-based inside the module
  - **Analyst:** a reasoning loop that owns the triage verdict — exploitable in this environment? priority? remediation SLA? — reusing the ReAct/data-sufficiency pattern
  - **Output contract:** a VM triage report payload plus the generic `outcome` (disposition + priority)
  - **Dedup key:** `(cve, asset, content-hash)` so a materially changed finding is re-reviewed while an unchanged one is not
- **Reuses the horizontals** — the identity capability (asset owner / access context) and the `Capabilities` registry — and adds VM-specific tooling: an asset-inventory data source and CVE/EPSS/KEV enrichment.
- **Registered in the `ModuleRegistry`** and reachable via `OrchestratorAgent` (explicit domain on the API, `accepts()` for free-form MCP chat).

## Capabilities

### New Capabilities
- `vuln-management-module`: the VM triage vertical (input schema, playbooks, analyst, report, dedup key)
- `asset-inventory-datasource`: a DataAgent over the asset/vuln inventory backend (VM-specific horizontal data)
- `vuln-intel-enrichment`: CVE/EPSS/KEV enrichment capability

### Modified Capabilities
- None to SIEM — this is purely additive, which is the point of the module model

### Non-Goals
- Remediation actions of any kind — Benny is investigation-only by design
- Changing SIEM behavior

## Impact

- **Depends on:** `module-contract-and-orchestrator`, `capability-layer`, `identity-capability`, and ideally `investigation-idempotency` (for the VM dedup key). This is the last slice.
- `src/modules/vuln_mgmt/`: analyst, schemas (`Finding`, VM report), runbooks
- `src/capabilities/`: asset-inventory data source + CVE/EPSS/KEV enrichment providers
- Validates the central claim: adding a domain = adding a module, not modifying the core
