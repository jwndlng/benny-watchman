"""Abstract base class for harness investigation cases."""

from __future__ import annotations

import asyncio
import os
import tempfile
import traceback
from abc import ABC, abstractmethod

from src.modules.siem.analyst import AnalystAgent
from src.capabilities.data.sqlite_data_agent import SQLiteDataAgent
from src.core.orchestration.runbook_registry import RunbookRegistry
from src.modules.siem.alert import Alert
from src.modules.siem.incident_report import Severity, Verdict
from tests.harness.judge import Judge
from tests.harness.schema import CaseResult
from tests.harness.seeder.base_dataset import BaseDataset


class BaseCase(ABC):
    name: str
    runbook_name: str = "generic"
    expected_verdict: Verdict | None = None
    severity_range: tuple[Severity, Severity] | None = None

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

            data_agent = SQLiteDataAgent(
                name="security_logs", model=model, db_path=db_path
            )
            asyncio.run(data_agent.initialize())

            agent = AnalystAgent(model=model, runbook=runbook, data_agents=[data_agent])
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
