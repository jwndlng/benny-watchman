"""Harness CLI runner — executes investigation cases and reports results.

Usage:
    uv run python tests/harness/main.py [--model MODEL] [--case CASE_NAME]

Exit code 1 if any case fails.
"""

import argparse
import sys

from src.config import Config
from src.runbook.registry import RunbookRegistry
from tests.harness.cases.base_case import BaseCase
from tests.harness.cases.case_brute_force import BruteForceCase
from tests.harness.schema import CaseResult, HarnessReport

ALL_CASES: list[BaseCase] = [
    BruteForceCase(),
]

_PASS = "PASS"
_FAIL = "FAIL"
_SKIP = "SKIP"


class HarnessManager:
    def run_all(
        self, model: str, registry: RunbookRegistry, filter_name: str | None = None
    ) -> HarnessReport:
        cases = ALL_CASES
        if filter_name:
            cases = [c for c in cases if c.name == filter_name]
            if not cases:
                print(
                    f"No case named '{filter_name}'. Available: {[c.name for c in ALL_CASES]}"
                )
                sys.exit(1)

        results: list[CaseResult] = []
        for case in cases:
            print(f"  Running {case.name} ...", end=" ", flush=True)
            result = case.run(model=model, registry=registry)
            status = (
                _PASS
                if result.passed is True
                else (_FAIL if result.passed is False else _SKIP)
            )
            print(status)
            results.append(result)

        passed = sum(1 for r in results if r.passed is True)
        failed = sum(1 for r in results if r.passed is False)
        skipped = sum(1 for r in results if r.passed is None)

        return HarnessReport(
            total=len(results),
            passed=passed,
            failed=failed,
            skipped=skipped,
            results=results,
        )


def _print_report(report: HarnessReport) -> None:
    print()
    print(f"{'Case':<35} {'Verdict':<20} {'Severity':<15} {'Conf':>5}  {'Result'}")
    print("-" * 90)
    for r in report.results:
        status = _PASS if r.passed is True else (_FAIL if r.passed is False else _SKIP)
        conf = f"{r.confidence:.0%}"
        print(
            f"{r.case_name:<35} {r.verdict.value:<20} {r.severity.value:<15} {conf:>5}  {status}"
        )
        if r.error:
            for line in r.error.strip().splitlines()[-5:]:
                print(f"  {line}")
    print("-" * 90)
    print(
        f"Total: {report.total}  Passed: {report.passed}  Failed: {report.failed}  No-assertion: {report.skipped}"
    )


if __name__ == "__main__":
    cfg = Config()

    parser = argparse.ArgumentParser(description="Run harness investigation cases")
    parser.add_argument(
        "--model",
        default=cfg.agent.model,
        help=f"LLM model identifier (default: {cfg.agent.model})",
    )
    parser.add_argument(
        "--case",
        default=None,
        help="Run only the named case (e.g. brute_force_ssh)",
    )
    args = parser.parse_args()

    registry = RunbookRegistry()
    registry.load(cfg.runbooks.path)

    print(f"Harness — model: {args.model}")
    print(f"Cases: {[c.name for c in ALL_CASES]}")
    print()

    manager = HarnessManager()
    report = manager.run_all(model=args.model, registry=registry, filter_name=args.case)

    _print_report(report)

    sys.exit(0 if report.failed == 0 else 1)
