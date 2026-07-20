"""The triage-loop — drives a TriagePlatform through the orchestrator.

Domain-agnostic: it only touches ``OrchestratorAgent.handle`` and the generic
``outcome`` on the returned Investigation, so it works for any module. Lives in
``platforms/`` (not ``core/``) so that core stays unaware of the platform layer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import logfire

from src.adapters.platforms.base import CaseStatus, CloseReason, TriageStatus

if TYPE_CHECKING:
    from src.core.orchestration.orchestrator import OrchestratorAgent
    from src.adapters.platforms.base import TriagePlatform
    from src.schemas.investigation import Investigation

# Disposition → close reason. Anything unmapped closes as OTHER (inconclusive).
_DISPOSITION_REASONS = {
    "false_positive": CloseReason.FALSE_POSITIVE,
    "benign": CloseReason.BENIGN_POSITIVE,
    "not_exploitable": CloseReason.BENIGN_POSITIVE,
    "true_positive": CloseReason.TRUE_POSITIVE,
    "exploitable": CloseReason.TRUE_POSITIVE,
    "inconclusive": CloseReason.OTHER,
}


def _close_reason(disposition: str | None) -> CloseReason:
    """Map an investigation disposition to the reason the item is closed with."""
    if not disposition:
        return CloseReason.NONE
    return _DISPOSITION_REASONS.get(disposition, CloseReason.OTHER)


# Reasons where Benny fully resolved the item — the case is closed too. Anything
# else (true positive, inconclusive) leaves the case IN_PROGRESS for a human.
_RESOLVED_REASONS = {CloseReason.FALSE_POSITIVE, CloseReason.BENIGN_POSITIVE}


def _summarize(investigation: Investigation) -> str:
    report = investigation.report or {}
    summary = report.get("summary", "")
    disposition = investigation.outcome.disposition if investigation.outcome else "unknown"
    return f"Benny triage — {disposition}: {summary}".strip()


def _write_back(platform: TriagePlatform, item_id: str, inv: Investigation) -> None:
    """Shared write-back for a fresh investigation: case, comment, severity, close.

    Case-always for traceability. The case follows Benny's work: opened, moved to
    IN_PROGRESS while triaging, then CLOSED if he resolved it (benign) or left
    IN_PROGRESS for a human if escalated. The alert lifecycle always ends CLOSED
    with a disposition-derived reason; a TRUE_POSITIVE escalates via the case
    (severity + open case), not by leaving the alert open.
    """
    platform.create_case(item_id, inv)
    platform.set_case_status(item_id, CaseStatus.IN_PROGRESS)  # Benny is working the case
    platform.comment(item_id, _summarize(inv))
    disposition: str | None = None
    if inv.outcome is not None:
        platform.set_severity(item_id, inv.outcome.priority)
        disposition = inv.outcome.disposition
    reason = _close_reason(disposition)
    platform.set_status(item_id, TriageStatus.CLOSED, reason=reason)
    # Benny resolved it (benign) → close the case; escalations stay IN_PROGRESS for a human.
    if reason in _RESOLVED_REASONS:
        platform.set_case_status(item_id, CaseStatus.CLOSED)


def run_once(
    orchestrator: OrchestratorAgent,
    platform: TriagePlatform,
    hint: str,
    limit: int | None = None,
) -> list[Investigation]:
    """Process open work items once: acknowledge, investigate, then write back.

    Each item is acknowledged before investigation (claimed, "Benny is on it").
    Review-once is the platform's job (a triaged alert won't be re-surfaced by
    `fetch_open`), so the loop does not DB-dedup — every produced investigation is
    written back via the shared helper and closed with a disposition-derived
    reason; an unresolved item is left ACKNOWLEDGED for a human. `limit` bounds how
    many items a single pass triages (None → platform default).
    """
    handled: list[Investigation] = []
    raws = platform.fetch_open(limit) if limit is not None else platform.fetch_open()
    for raw in raws:
        item_id = raw["id"]
        platform.acknowledge(item_id)  # claim before investigating
        # dedup=False: the platform owns review-once (fetch_open won't re-surface a
        # triaged alert), so the loop always investigates and writes back.
        result = orchestrator.handle(raw, hint=hint, dedup=False)

        if result.investigation is None:
            # No module produced a verdict — leave ACKNOWLEDGED so a human sees it.
            logfire.info("triage-loop: no module resolved, left acknowledged", item_id=item_id, hint=hint)
            continue

        inv = result.investigation
        _write_back(platform, item_id, inv)
        handled.append(inv)
    return handled
