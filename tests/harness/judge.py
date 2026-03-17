"""Case result evaluator.

Currently assertion-based. Will become an LLM-as-judge scorer in a future milestone.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.schemas.incident_report import IncidentReport, Severity

if TYPE_CHECKING:
    from tests.harness.cases.base_case import BaseCase

_SEVERITY_RANK: dict[Severity, int] = {
    Severity.CRITICAL: 5,
    Severity.HIGH: 4,
    Severity.MEDIUM: 3,
    Severity.LOW: 2,
    Severity.INFORMATIONAL: 1,
}


class Judge:
    def evaluate(self, case: "BaseCase", report: IncidentReport) -> bool | None:
        """Return True/False if assertions are defined, None if the case has no expectations."""
        if (
            case.expected_verdict is not None
            and report.verdict != case.expected_verdict
        ):
            return False
        if case.severity_range is not None:
            min_sev, max_sev = case.severity_range
            rank = _SEVERITY_RANK[report.severity]
            if not (_SEVERITY_RANK[min_sev] <= rank <= _SEVERITY_RANK[max_sev]):
                return False
        if case.expected_verdict is not None or case.severity_range is not None:
            return True
        return None
