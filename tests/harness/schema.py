"""Pydantic models for harness case results and reports."""

from pydantic import BaseModel

from src.schemas.incident_report import Severity, Verdict


class CaseResult(BaseModel):
    case_name: str
    passed: bool | None  # None = no assertion defined
    verdict: Verdict
    severity: Severity
    confidence: float
    summary: str
    findings: list[str]
    error: str | None = None


class HarnessReport(BaseModel):
    total: int
    passed: int
    failed: int
    skipped: int  # cases that raised an exception
    results: list[CaseResult]
