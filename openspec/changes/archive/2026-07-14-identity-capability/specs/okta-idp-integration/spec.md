## MODIFIED Requirements

### Requirement: AnalystAgent.lookup_user delegates to OktaClient when configured
`AnalystAgent` SHALL accept an optional `identity: IdentityCapability | None = None` parameter (replacing the former `okta_client: OktaClient | None`). Its `lookup_user` tool SHALL delegate to `IdentityCapability.lookup_user`, which returns the Okta-sourced `UserProfile` when available and `None` otherwise. The analyst SHALL NOT reference the Okta client directly — the client is wrapped by an `IdentityCapability` built at the composition root and injected via `Capabilities`.

#### Scenario: Identity configured and user found
- **WHEN** `AnalystAgent` is constructed with an `IdentityCapability` whose backing Okta client returns a `UserProfile`
- **THEN** `lookup_user(username)` returns that `UserProfile`

#### Scenario: Identity configured but user not found
- **WHEN** the backing Okta client returns `None`
- **THEN** `lookup_user(username)` returns `None`

#### Scenario: Identity not configured
- **WHEN** `AnalystAgent` is constructed without an identity capability (default `None`)
- **THEN** `lookup_user(username)` returns `None`
