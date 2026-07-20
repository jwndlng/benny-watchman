## MODIFIED Requirements

### Requirement: VM reuses the DataAgent pattern and owns its intel tool
The VM analyst SHALL consult an asset/vuln inventory via a `DataAgent` selected from `Capabilities.data` (dev: a seeded SQLite source named `asset_inventory`). The asset-inventory source SHALL be config-gated: the composition root builds it if and only if `[vuln]` is present. When `[vuln]` is absent, `VulnModule` SHALL remain registered and routable, and its analyst SHALL run intel-only — with the vuln-intel tool but no asset query tool. Threat-intel enrichment (CVE/EPSS/KEV) SHALL be a VM-owned composite tool (deterministic; a stub in dev), exposed to the analyst — not a shared horizontal capability.

#### Scenario: VM analyst has data and intel tools when configured
- **WHEN** the VM module builds its analyst with `[vuln]` present
- **THEN** the analyst can query the `asset_inventory` data source and call the vuln-intel tool

#### Scenario: VM runs intel-only when the asset source is unconfigured
- **WHEN** the app starts with `[vuln]` absent and a finding is submitted to `POST /findings`
- **THEN** `VulnModule` still handles it and its analyst is built with the vuln-intel tool but no asset query tool
