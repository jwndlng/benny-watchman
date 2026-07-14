## 1. Identity capability

- [x] 1.1 Add `IdentityCapability` (composite `lookup_user` over `OktaClient`) in `src/capabilities/identity/assessment.py`
- [x] 1.2 Change `Capabilities.identity` to `IdentityCapability | None`

## 2. Wire modules & composition root

- [x] 2.1 `AnalystAgent` depends on `identity: IdentityCapability | None` (was `okta_client`); `lookup_user` delegates to it
- [x] 2.2 `SIEMModule.investigate` passes `identity=caps.identity`
- [x] 2.3 `create_app` builds `IdentityCapability(okta_client)` into `Capabilities`

## 3. Tests & verify

- [x] 3.1 Unit-test `IdentityCapability` (delegation + None-without-client)
- [x] 3.2 Update `AnalystAgent.lookup_user` tests to the identity capability
- [x] 3.3 `make test` green, `make lint` clean
