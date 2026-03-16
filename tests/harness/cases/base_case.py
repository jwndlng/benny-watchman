"""Abstract base class for harness investigation cases."""

from __future__ import annotations

import os
import tempfile
import traceback
from abc import ABC, abstractmethod

from src.agents.analyst_agent import AnalystAgent
from src.runbook.registry import RunbookRegistry
from src.schemas.alert import Alert
from src.schemas.incident_report import Severity, Verdict
from tests.harness.judge import Judge
from tests.harness.schema import CaseResult
from tests.harness.seeder.base_dataset import BaseDataset


class BaseCase(ABC):
    name: str
    runbook_name: str = "generic"
    expected_verdict: Verdict | None = None
    expected_severity: Severity | None = None

    @property
    @abstractmethod
    def dataset(self) -> BaseDataset: ...

    @abstractmethod
    def alert(self) -> Alert: ...

    def run(self, model: str, registry: RunbookRegistry) -> CaseResult:
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            self.dataset.load(db_path)

            runbook = registry.get(self.runbook_name) or registry.get("generic")
            if runbook is None:
                raise RuntimeError(
                    f"No runbook found for '{self.runbook_name}' and no 'generic' fallback."
                )

            agent = AnalystAgent(model=model, runbook=runbook, db_path=db_path)
            investigation = agent.investigate(self.alert())
            report = investigation.report

            passed = Judge().evaluate(self, report)
            return CaseResult(
                case_name=self.name,
                passed=passed,
                verdict=report.verdict,
                severity=report.severity,
                confidence=report.confidence,
                summary=report.summary,
                findings=report.findings,
            )
        except Exception:
            return CaseResult(
                case_name=self.name,
                passed=False,
                verdict=Verdict.INCONCLUSIVE,
                severity=Severity.INFORMATIONAL,
                confidence=0.0,
                summary="",
                findings=[],
                error=traceback.format_exc(),
            )
        finally:
            os.unlink(db_path)
