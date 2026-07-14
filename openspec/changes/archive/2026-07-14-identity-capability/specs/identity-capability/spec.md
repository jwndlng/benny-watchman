## ADDED Requirements

### Requirement: IdentityCapability provides composite identity lookups
The system SHALL provide an `IdentityCapability` exposing `lookup_user(username) -> UserProfile | None`, backed by an optional IDP client (Okta). It SHALL be a deterministic composite tool (no LLM) and SHALL be consumable by any module via the `Capabilities` container.

#### Scenario: Delegates to the IDP client
- **WHEN** `lookup_user(username)` is called on an `IdentityCapability` backed by an Okta client
- **THEN** it returns the `UserProfile` produced by the client's `get_user(username)`

#### Scenario: No IDP configured
- **WHEN** `lookup_user(username)` is called on an `IdentityCapability` with no client
- **THEN** it returns `None` without error

---

### Requirement: Capabilities exposes identity to modules
`Capabilities.identity` SHALL hold an optional `IdentityCapability`, built once at the composition root, so any module's analyst can consult identity context without constructing its own IDP client.

#### Scenario: SIEM analyst consumes the identity capability
- **WHEN** the SIEM module builds its analyst
- **THEN** the analyst's `lookup_user` tool delegates to `caps.identity.lookup_user`, not to an `OktaClient` directly
