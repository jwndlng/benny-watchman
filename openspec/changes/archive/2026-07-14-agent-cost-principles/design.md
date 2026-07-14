## Context

The architecture leans on multi-agent delegation; the dominant cost is context re-sent each turn. Without a written rule, the agent tree can quietly become an expensive N-deep nest.

## Goals / Non-Goals

**Goals:** codify the compression-boundary rule and the horizontal/vertical agent model as durable project guidance.

**Non-Goals:** any code change — this is guidance only.

## Decisions

- The guidance lives in **AGENT.md** (loaded as project instructions), so it is present where code is written and outlives any single change.
- A **node-type decision table** (inline tool / composite tool / sub-agent / analyst) plus the two guardrails ("needs reasoning ≠ has a parameter"; "don't shard the core reasoning") are the canonical reference.

## Risks / Trade-offs

- **Guidance drifts from code** → mitigated by colocating it next to the existing Agent Design Principles in AGENT.md; revisit on architecture changes.
