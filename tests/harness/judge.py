"""Case result evaluator.

Currently assertion-based. Will become an LLM-as-judge scorer in a future milestone.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.schemas.incident_report import IncidentReport

if TYPE_CHECKING:
    from tests.harness.cases.base_case import BaseCase


class Judge:
    def evaluate(self, case: "BaseCase", report: IncidentReport) -> bool | None:
        """Return True/False if assertions are defined, None if the case has no expectations."""
        if (
            case.expected_verdict is not None
            and report.verdict != case.expected_verdict
        ):
            return False
        if (
            case.expected_severity is not None
            and report.severity != case.expected_severity
        ):
            return False
        if case.expected_verdict is not None or case.expected_severity is not None:
            return True
        return None
