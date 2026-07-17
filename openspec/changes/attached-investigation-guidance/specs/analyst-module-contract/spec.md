## REMOVED Requirements

### Requirement: Runbook selection remains internal to the module
**Reason**: Runbooks are removed. Per-item direction now travels attached to the work item as `guidance`, and the analyst's general method is a Benny-owned in-repo prompt — see the `investigation-guidance` capability.
**Migration**: Delete `RunbookRegistry` and the `src/modules/*/runbooks/` files. The `generic.md` content becomes the module's baked-in analyst method; per-type steering moves to the item's `guidance` field.

## ADDED Requirements

### Requirement: The analyst method and guidance are internal to the module
The system SHALL keep the analyst's steering internal to the module and off the `AnalystModule` contract: the general investigation method is the module's own in-repo persona, and per-item direction arrives via the item's `guidance` field. Neither is exposed through `name`/`input_type`/`accepts`/`investigate`.

#### Scenario: Steering is not on the contract
- **WHEN** the `AnalystModule` contract is inspected
- **THEN** it exposes only `name`, `input_type`, `accepts`, and `investigate` — no runbook or guidance selection surface

#### Scenario: Method drives the persona
- **WHEN** a module investigates an item
- **THEN** the analyst persona is the module's general method, and any item `guidance` is applied as a lead within that method
