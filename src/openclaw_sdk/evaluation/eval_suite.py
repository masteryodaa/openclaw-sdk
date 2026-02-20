"""Evaluation suite for systematic agent testing."""

from __future__ import annotations

from dataclasses import dataclass, field

from openclaw_sdk.core.types import ExecutionResult
from openclaw_sdk.evaluation.evaluators import Evaluator


@dataclass
class EvalCase:
    """A single evaluation case: a query paired with an evaluator."""

    query: str
    evaluator: Evaluator
    name: str | None = None
    tags: list[str] = field(default_factory=list)


@dataclass
class EvalCaseResult:
    """Result of running a single evaluation case."""

    case: EvalCase
    passed: bool
    result: ExecutionResult


@dataclass
class EvalReport:
    """Aggregated report from running an evaluation suite."""

    name: str
    total: int
    passed: int
    failed: int
    case_results: list[EvalCaseResult]

    @property
    def pass_rate(self) -> float:
        """Return the fraction of cases that passed (0.0 to 1.0)."""
        return self.passed / self.total if self.total > 0 else 0.0


class EvalSuite:
    """A collection of evaluation cases that can be run against an agent."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._cases: list[EvalCase] = []

    def add_case(self, case: EvalCase) -> None:
        """Add an evaluation case to the suite."""
        self._cases.append(case)

    def evaluate(self, results: list[ExecutionResult]) -> EvalReport:
        """Evaluate a list of pre-collected results against the registered cases."""
        case_results: list[EvalCaseResult] = []
        for case, result in zip(self._cases, results):
            passed = case.evaluator.evaluate(result)
            case_results.append(
                EvalCaseResult(case=case, passed=passed, result=result)
            )
        passed_count = sum(1 for cr in case_results if cr.passed)
        return EvalReport(
            name=self.name,
            total=len(case_results),
            passed=passed_count,
            failed=len(case_results) - passed_count,
            case_results=case_results,
        )

    async def run(self, agent: object) -> EvalReport:
        """Run all cases against an agent and return an evaluation report.

        The agent must have an async ``execute(query: str)`` method that
        returns an ``ExecutionResult``.  Duck typing is used so any compatible
        object works.
        """
        results: list[ExecutionResult] = []
        for case in self._cases:
            result = await agent.execute(case.query)  # type: ignore[attr-defined]
            results.append(result)
        return self.evaluate(results)
