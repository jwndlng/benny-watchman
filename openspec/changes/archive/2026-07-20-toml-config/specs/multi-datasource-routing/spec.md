## ADDED Requirements

### Requirement: Configured data sources are authoritative
The composition root SHALL build log DataAgents from configuration: a log data source runs if and only if its configuration section is present (`[data.sqlite]`, `[data.elastic]`). The system SHALL NOT build an always-on default data source, and there SHALL be no separate, ignored engine selector. Enabling or disabling a source SHALL be done by adding or removing its section.

#### Scenario: Only configured sources are registered
- **WHEN** the app starts with `[data.elastic]` present and `[data.sqlite]` absent
- **THEN** only the Elastic log DataAgent is registered and no SQLite log agent is built

#### Scenario: Multiple configured sources both register
- **WHEN** both `[data.sqlite]` and `[data.elastic]` sections are present
- **THEN** a log DataAgent is registered for each, with distinct `name`s

#### Scenario: No configured log source
- **WHEN** neither `[data.sqlite]` nor `[data.elastic]` is present
- **THEN** no log DataAgent is registered and the analyst is given no log query tool
