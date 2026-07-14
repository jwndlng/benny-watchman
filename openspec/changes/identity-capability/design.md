## Context

Identity/access lookups (`lookup_user`) lived as a method on the SIEM `AnalystAgent`, bound to `OktaClient`. Every triage domain needs identity context, so it should be a shared horizontal capability rather than SIEM-analyst-private.

## Goals / Non-Goals

**Goals:** extract a reusable `IdentityCapability` consumed via `Capabilities`; keep behavior identical.

**Non-Goals:** promoting to an LLM `IDPAgent`; adding new lookups (app permissions, admin grants) — deferred until the questions justify it.

## Decisions

- **`IdentityCapability`** (`src/capabilities/identity/assessment.py`) is a **composite deterministic tool** wrapping `OktaClient`, exposing `lookup_user(username) -> UserProfile | None`. Per the compression-boundary rule, a fixed pipeline of deterministic lookups is a composite tool, not an LLM sub-agent — and callers depend on this interface, so it can graduate to an IDPAgent later without changing them.
- **`AnalystAgent` depends on `identity: IdentityCapability | None`** (replacing `okta_client: OktaClient`). Its `lookup_user` tool delegates to the capability. `Capabilities.identity` holds the `IdentityCapability`, built once at the composition root.

## Risks / Trade-offs

- **Thin wrapper today** → Accepted: the seam is the point. It makes identity reusable across modules and swappable to an agent later, at negligible cost now.
