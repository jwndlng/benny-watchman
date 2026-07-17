"""The triage-loop — drives a TriagePlatform through the orchestrator.

Domain-agnostic: it only touches ``OrchestratorAgent.handle`` and the generic
``outcome`` on the returned Investigation, so it works for any module. Lives in
``platforms/`` (not ``core/``) so that core stays unaware of the platform layer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import logfire

from src.adapters.platforms.base import TriageStatus

if TYPE_CHECKING:
    from src.core.orchestration.orchestrator import OrchestratorAgent
    from src.adapters.platforms.base import TriagePlatform
    from src.schemas.investigation import Investigation

# Dispositions Benny may auto-close. Anything else escalates — when unsure, escalate.
_BENIGN_DISPOSITIONS = {"false_positive", "benign", "not_exploitable"}


def _summarize(investigation: Investigation) -> str:
    report = investigation.report or {}
    summary = report.get("summary", "")
    disposition = investigation.outcome.disposition if investigation.outcome else "unknown"
    return f"Benny triage — {disposition}: {summary}".strip()


def run_once(
    orchestrator: OrchestratorAgent,
    platform: TriagePlatform,
    hint: str,
    limit: int | None = None,
) -> list[Investigation]:
    """Process open work items once: investigate, then write the outcome back.

    Case-always for traceability; benign/false-positive → CLOSED, otherwise
    ESCALATED. Only freshly-created investigations are written back — a re-seen
    (deduplicated) or unresolvable item is skipped. `limit` bounds how many items
    a single pass triages (None → the platform's default).
    """
    handled: list[Investigation] = []
    raws = platform.fetch_open(limit) if limit is not None else platform.fetch_open()
    for raw in raws:
        item_id = raw["id"]
        result = orchestrator.handle(raw, hint=hint)
        if result.investigation is None:
            logfire.info("triage-loop: no module resolved", item_id=item_id, hint=hint)
            continue
        if not result.created:
            logfire.info("triage-loop: dedup hit, skipping write-back", item_id=item_id)
            continue

        inv = result.investigation
        platform.create_case(item_id, inv)
        platform.comment(item_id, _summarize(inv))
        disposition = ""
        if inv.outcome is not None:
            platform.set_severity(item_id, inv.outcome.priority)
            disposition = inv.outcome.disposition
        platform.set_status(
            item_id,
            TriageStatus.CLOSED if disposition in _BENIGN_DISPOSITIONS else TriageStatus.ESCALATED,
        )
        handled.append(inv)
    return handled
