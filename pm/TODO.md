# TODO: DESIGN.md Open Questions

## Section 6 — Testing & Evaluation

- [ ] **Feedback loop:** "Tweak the CONTEXT.md" after test failures is vague. Define a concrete process — who reviews the results, what metrics trigger a change, and how changes are approved.
- [ ] **Regression testing:** How do we ensure fixing one scenario doesn't break others? Should the full Golden Dataset run on every change to skills/context (e.g., as part of CI)?
- [ ] **Golden dataset sources:** Candidate log datasets for building evaluation fixtures:
  - https://github.com/scalyr/samples — sample logs across various sources
  - https://github.com/sbousseaden/EVTX-ATTACK-SAMPLES — Windows EVTX samples mapped to MITRE ATT&CK
  - https://csr.lanl.gov/data/ — LANL anonymised enterprise network/auth logs (research grade)

## Missing Sections

- [ ] **Output Schema:** Define the triage report structure — JSON fields, severity enum, confidence scores, recommended actions format. This is what the caller receives and needs to be stable.
- [ ] **Deployment & CI/CD:** How are new skills, context updates, and allowlist changes rolled out? Docker build pipeline, image tagging strategy, rollback process.
- [ ] **Cost Tracking:** LLM API spend per investigation. The structured logs go to the data lake — should token counts and cost be included per request for budget monitoring?
- [ ] **Concurrency:** Can the system handle multiple alerts in parallel? One container per investigation, or a single container processing a queue sequentially?
- [ ] **DB Migrations:** No migration tooling in place. Alembic covers SQLite/Postgres well; Clickhouse needs separate handling (e.g., `clickhouse-migrations` or raw DDL scripts) since it doesn't map cleanly onto SQLAlchemy's migration model. Current JSON blob schema is simple enough that this isn't urgent.
