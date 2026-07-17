## MODIFIED Requirements

### Requirement: Platform is selected by configuration
The composition root SHALL build `ElasticSecurityPlatform` when Kibana triage settings are present in configuration (the `[kibana]` section — `url` and `case_owner`, with the API key sourced from its environment alias), and fall back to `InMemoryTriagePlatform` otherwise. Credentials SHALL be scoped to alerts read + signal-status write + cases — never remediation.

#### Scenario: Elastic selected when configured
- **WHEN** the app starts with the `[kibana]` section and its API key present
- **THEN** `run_once` operates against `ElasticSecurityPlatform`

#### Scenario: In-memory fallback when unconfigured
- **WHEN** the app starts without Kibana triage settings
- **THEN** the in-memory platform is used and no Elastic calls are made

## ADDED Requirements

### Requirement: Kibana configuration may target a non-default space
The Kibana base URL MAY include a Kibana space prefix (`/s/<space-id>`); all Kibana API calls SHALL then operate within that space. When no space prefix is present, calls operate in the default space.

#### Scenario: Space prefix scopes API calls
- **WHEN** the Kibana `url` is configured as `https://host/s/isec`
- **THEN** signals search, signal-status, and cases calls are issued under the `/s/isec` prefix

#### Scenario: No prefix uses the default space
- **WHEN** the Kibana `url` has no `/s/<space-id>` segment
- **THEN** calls operate in the default Kibana space
