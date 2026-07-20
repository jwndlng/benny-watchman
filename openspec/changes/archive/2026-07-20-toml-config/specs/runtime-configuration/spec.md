## ADDED Requirements

### Requirement: TOML is the canonical configuration source
The system SHALL load configuration from a TOML file (`config.toml`) into typed settings models via `pydantic-settings`. All non-secret settings SHALL be expressible in TOML. Configuration SHALL be validated when settings are constructed; an invalid or missing-required value SHALL raise an error that aborts startup rather than being silently defaulted.

#### Scenario: Valid config loads into typed settings
- **WHEN** the application starts with a well-formed `config.toml`
- **THEN** settings load as typed models and startup proceeds

#### Scenario: Invalid config fails fast
- **WHEN** a required setting is missing or a value has the wrong type
- **THEN** a validation error is raised and startup aborts before any requests are served

### Requirement: Precedence is env over TOML over defaults
The system SHALL resolve each setting with precedence environment variable > TOML value > built-in default, so any setting can be overridden per-environment without editing TOML.

#### Scenario: Env overrides TOML
- **WHEN** a setting has both a TOML value and a corresponding environment variable
- **THEN** the environment variable value is used

#### Scenario: Default applies when unset
- **WHEN** a setting is absent from both env and TOML and has a default
- **THEN** the default is used

### Requirement: Secrets are sourced only from environment variables
The system SHALL source secret values (model/API keys, tokens, private keys) exclusively from environment variables, via each secret field's environment alias (e.g. `KIBANA_TRIAGE_API_KEY`, `ELASTIC_API_KEY`, `AGENT_MODEL_API_KEY`, `OKTA_CLIENT_ID`, `OKTA_PRIVATE_KEY`, `MCP_BEARER_TOKEN`). Secret values SHALL NOT appear in `config.toml.example`.

#### Scenario: Secret read from its env alias
- **WHEN** `KIBANA_TRIAGE_API_KEY` is set in the environment
- **THEN** it populates the Kibana API key setting without any TOML entry

#### Scenario: Example config carries no secrets
- **WHEN** `config.toml.example` is inspected
- **THEN** it contains only non-secret settings — no keys, tokens, or private keys

### Requirement: config.toml.example is committed and config.toml is git-ignored
The repository SHALL commit a `config.toml.example` and SHALL git-ignore `config.toml`; users copy the example to `config.toml`. When `config.toml` is absent, the system SHALL fall back to environment variables and defaults so pure-env deployments and tests work without a file.

#### Scenario: Example tracked, real config ignored
- **WHEN** the repository is inspected
- **THEN** `config.toml.example` is tracked by git and `config.toml` is ignored

#### Scenario: Missing config.toml falls back to env + defaults
- **WHEN** the application starts with no `config.toml` present and required values supplied via env
- **THEN** settings load from env + defaults and startup proceeds
