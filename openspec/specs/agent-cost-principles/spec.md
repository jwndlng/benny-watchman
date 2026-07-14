# agent-cost-principles Specification

## Purpose
TBD - created by archiving change agent-cost-principles. Update Purpose after archive.
## Requirements
### Requirement: Project guidance documents the compression-boundary rule
The project guidance (`AGENT.md`) SHALL document the compression-boundary rule and the horizontal/vertical agent model, including a decision table mapping a unit of work to one of: inline tool, composite deterministic tool, sub-agent (LLM loop), or the analyst itself.

#### Scenario: Guidance present for contributors
- **WHEN** a contributor reads `AGENT.md`
- **THEN** the compression-boundary rule, the two guardrails, and the node-type decision table are present

