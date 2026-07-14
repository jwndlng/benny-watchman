## Why

Identity/access context — "who is this user, what can they access, do they own this asset" — is needed by every triage domain, not just SIEM. Today it is an `AnalystAgent` method (`lookup_user`) bound to the SIEM analyst. To make it reusable across modules and to follow the compression-boundary rule, it should be a shared horizontal capability.

Implements decision 5 of the `modular-soc-architecture` design.

## What Changes

- **Extract `lookup_user` into a composite `IdentityAssessment` capability.** It bundles the identity lookups (profile, manager, and — as they grow — application permissions, admin grants, group memberships) behind a single call, so a consuming analyst pays one round-trip instead of orchestrating N lookups turn-by-turn inside its own growing context. (Compression-boundary rule: a fixed pipeline of deterministic calls is a composite tool, not an LLM sub-agent.)
- **One capability call, swappable internals.** Analysts consume it as a single entry in the `Capabilities` registry whose implementation can later become an `IDPAgent` (an LLM loop) without changing callers — promoted only if access questions become reason-as-you-go and produce a *judgment* rather than *facts*.
- Benny already does the mini-version: `lookup_user` fires two Okta SDK calls (user + manager) behind one tool and returns one `UserProfile`. This generalizes that pattern into a first-class capability.

## Capabilities

### New Capabilities
- `identity-capability`: a shared `IdentityAssessment` composite tool exposed via the `Capabilities` registry, consumable by any module

### Modified Capabilities
- `okta-idp-integration`: `lookup_user` is no longer an `AnalystAgent` method; the Okta-backed lookup is exposed as a horizontal capability rather than a SIEM-analyst tool

## Impact

- **Depends on:** `module-contract-and-orchestrator` (the `Capabilities` registry and `build_analyst(caps)` injection point)
- `src/capabilities/identity/`: add `assessment.py` (the composite `IdentityAssessment`); `OktaClient` and `UserProfile` already live here after slice 1
- SIEM module: consumes the identity capability via `caps` instead of a bespoke `lookup_user` method
- No behavioral change to the identity *data* — this is a relocation + generalization, keeping the "return None on error, fall back gracefully" contract
