"""Tests for the evaluation framework (EvalSuite + evaluators)."""

from __future__ import annotations

from openclaw_sdk.core.types import ExecutionResult
from openclaw_sdk.evaluation import (
    ContainsEvaluator,
    EvalCase,
    EvalCaseResult,
    EvalReport,
    EvalSuite,
    ExactMatchEvaluator,
    LengthEvaluator,
    RegexEvaluator,
)


def _result(content: str) -> ExecutionResult:
    """Helper to build a minimal ExecutionResult with given content."""
    return ExecutionResult(success=True, content=content)


# ---------------------------------------------------------------------------
# ContainsEvaluator
# ---------------------------------------------------------------------------


class TestContainsEvaluator:
    def test_contains_case_insensitive(self) -> None:
        ev = ContainsEvaluator("hello")
        assert ev.evaluate(_result("Say Hello World")) is True

    def test_contains_case_insensitive_missing(self) -> None:
        ev = ContainsEvaluator("goodbye")
        assert ev.evaluate(_result("Hello World")) is False

    def test_contains_case_sensitive_match(self) -> None:
        ev = ContainsEvaluator("Hello", case_sensitive=True)
        assert ev.evaluate(_result("Hello World")) is True

    def test_contains_case_sensitive_mismatch(self) -> None:
        ev = ContainsEvaluator("hello", case_sensitive=True)
        assert ev.evaluate(_result("Hello World")) is False

    def test_contains_empty_expected(self) -> None:
        ev = ContainsEvaluator("")
        assert ev.evaluate(_result("anything")) is True

    def test_contains_empty_content(self) -> None:
        ev = ContainsEvaluator("x")
        assert ev.evaluate(_result("")) is False

    def test_contains_both_empty(self) -> None:
        ev = ContainsEvaluator("")
        assert ev.evaluate(_result("")) is True


# ---------------------------------------------------------------------------
# ExactMatchEvaluator
# ---------------------------------------------------------------------------


class TestExactMatchEvaluator:
    def test_exact_match_strip(self) -> None:
        ev = ExactMatchEvaluator("hello")
        assert ev.evaluate(_result("  hello  ")) is True

    def test_exact_match_no_strip(self) -> None:
        ev = ExactMatchEvaluator("hello", strip=False)
        assert ev.evaluate(_result("  hello  ")) is False

    def test_exact_match_no_strip_exact(self) -> None:
        ev = ExactMatchEvaluator("hello", strip=False)
        assert ev.evaluate(_result("hello")) is True

    def test_exact_match_different(self) -> None:
        ev = ExactMatchEvaluator("hello")
        assert ev.evaluate(_result("goodbye")) is False

    def test_exact_match_empty(self) -> None:
        ev = ExactMatchEvaluator("")
        assert ev.evaluate(_result("")) is True

    def test_exact_match_whitespace_stripped(self) -> None:
        ev = ExactMatchEvaluator("  hello  ", strip=True)
        assert ev.evaluate(_result("hello")) is True


# ---------------------------------------------------------------------------
# RegexEvaluator
# ---------------------------------------------------------------------------


class TestRegexEvaluator:
    def test_regex_match(self) -> None:
        ev = RegexEvaluator(r"\d{3}-\d{4}")
        assert ev.evaluate(_result("Call 555-1234 now")) is True

    def test_regex_no_match(self) -> None:
        ev = RegexEvaluator(r"\d{3}-\d{4}")
        assert ev.evaluate(_result("no phone here")) is False

    def test_regex_full_string(self) -> None:
        ev = RegexEvaluator(r"^hello$")
        assert ev.evaluate(_result("hello")) is True

    def test_regex_full_string_no_match(self) -> None:
        ev = RegexEvaluator(r"^hello$")
        assert ev.evaluate(_result("hello world")) is False

    def test_regex_dot_star(self) -> None:
        ev = RegexEvaluator(r"error.*fatal")
        assert ev.evaluate(_result("error: something fatal happened")) is True

    def test_regex_empty_pattern(self) -> None:
        ev = RegexEvaluator(r"")
        assert ev.evaluate(_result("anything")) is True


# ---------------------------------------------------------------------------
# LengthEvaluator
# ---------------------------------------------------------------------------


class TestLengthEvaluator:
    def test_length_within_range(self) -> None:
        ev = LengthEvaluator(min_length=5, max_length=20)
        assert ev.evaluate(_result("hello world")) is True

    def test_length_too_short(self) -> None:
        ev = LengthEvaluator(min_length=10)
        assert ev.evaluate(_result("hi")) is False

    def test_length_too_long(self) -> None:
        ev = LengthEvaluator(max_length=5)
        assert ev.evaluate(_result("hello world")) is False

    def test_length_exact_min(self) -> None:
        ev = LengthEvaluator(min_length=5)
        assert ev.evaluate(_result("abcde")) is True

    def test_length_exact_max(self) -> None:
        ev = LengthEvaluator(max_length=5)
        assert ev.evaluate(_result("abcde")) is True

    def test_length_no_bounds(self) -> None:
        ev = LengthEvaluator()
        assert ev.evaluate(_result("")) is True
        assert ev.evaluate(_result("x" * 10000)) is True

    def test_length_min_only(self) -> None:
        ev = LengthEvaluator(min_length=0)
        assert ev.evaluate(_result("")) is True

    def test_length_zero_content(self) -> None:
        ev = LengthEvaluator(min_length=1)
        assert ev.evaluate(_result("")) is False


# ---------------------------------------------------------------------------
# EvalSuite.evaluate()
# ---------------------------------------------------------------------------


class TestEvalSuiteEvaluate:
    def test_all_pass(self) -> None:
        suite = EvalSuite("all-pass")
        suite.add_case(EvalCase(query="q1", evaluator=ContainsEvaluator("hello")))
        suite.add_case(EvalCase(query="q2", evaluator=ContainsEvaluator("world")))

        results = [_result("hello there"), _result("world here")]
        report = suite.evaluate(results)

        assert report.name == "all-pass"
        assert report.total == 2
        assert report.passed == 2
        assert report.failed == 0
        assert report.pass_rate == 1.0

    def test_all_fail(self) -> None:
        suite = EvalSuite("all-fail")
        suite.add_case(EvalCase(query="q1", evaluator=ExactMatchEvaluator("abc")))
        suite.add_case(EvalCase(query="q2", evaluator=ExactMatchEvaluator("xyz")))

        results = [_result("wrong"), _result("also wrong")]
        report = suite.evaluate(results)

        assert report.total == 2
        assert report.passed == 0
        assert report.failed == 2
        assert report.pass_rate == 0.0

    def test_mixed_pass_fail(self) -> None:
        suite = EvalSuite("mixed")
        suite.add_case(
            EvalCase(query="q1", evaluator=ContainsEvaluator("hello"), name="check-hello")
        )
        suite.add_case(
            EvalCase(query="q2", evaluator=ContainsEvaluator("missing"), name="check-missing")
        )
        suite.add_case(
            EvalCase(
                query="q3",
                evaluator=LengthEvaluator(min_length=1, max_length=100),
                name="check-length",
                tags=["length"],
            )
        )

        results = [_result("hello!"), _result("no match"), _result("some content")]
        report = suite.evaluate(results)

        assert report.total == 3
        assert report.passed == 2
        assert report.failed == 1
        assert report.pass_rate == 2.0 / 3.0

        # Verify individual case results
        assert report.case_results[0].passed is True
        assert report.case_results[0].case.name == "check-hello"
        assert report.case_results[1].passed is False
        assert report.case_results[1].case.name == "check-missing"
        assert report.case_results[2].passed is True
        assert report.case_results[2].case.tags == ["length"]

    def test_empty_suite(self) -> None:
        suite = EvalSuite("empty")
        report = suite.evaluate([])

        assert report.total == 0
        assert report.passed == 0
        assert report.failed == 0
        assert report.pass_rate == 0.0
        assert report.case_results == []


# ---------------------------------------------------------------------------
# EvalReport.pass_rate
# ---------------------------------------------------------------------------


class TestEvalReport:
    def test_pass_rate_all_passed(self) -> None:
        report = EvalReport(
            name="test", total=5, passed=5, failed=0, case_results=[]
        )
        assert report.pass_rate == 1.0

    def test_pass_rate_none_passed(self) -> None:
        report = EvalReport(
            name="test", total=5, passed=0, failed=5, case_results=[]
        )
        assert report.pass_rate == 0.0

    def test_pass_rate_half(self) -> None:
        report = EvalReport(
            name="test", total=4, passed=2, failed=2, case_results=[]
        )
        assert report.pass_rate == 0.5

    def test_pass_rate_empty(self) -> None:
        report = EvalReport(
            name="test", total=0, passed=0, failed=0, case_results=[]
        )
        assert report.pass_rate == 0.0


# ---------------------------------------------------------------------------
# EvalSuite.run() with mock agent
# ---------------------------------------------------------------------------


class TestEvalSuiteRun:
    async def test_run_with_mock_agent(self) -> None:
        """EvalSuite.run() calls agent.execute() for each case."""

        class FakeAgent:
            def __init__(self) -> None:
                self.calls: list[str] = []

            async def execute(self, query: str) -> ExecutionResult:
                self.calls.append(query)
                return _result(f"response to: {query}")

        agent = FakeAgent()
        suite = EvalSuite("run-test")
        suite.add_case(EvalCase(query="say hello", evaluator=ContainsEvaluator("hello")))
        suite.add_case(EvalCase(query="say world", evaluator=ContainsEvaluator("world")))

        report = await suite.run(agent)

        assert agent.calls == ["say hello", "say world"]
        assert report.total == 2
        assert report.passed == 2
        assert report.failed == 0

    async def test_run_empty_suite(self) -> None:
        """Running an empty suite returns an empty report."""

        class FakeAgent:
            async def execute(self, query: str) -> ExecutionResult:
                return _result(query)  # pragma: no cover

        agent = FakeAgent()
        suite = EvalSuite("empty-run")
        report = await suite.run(agent)

        assert report.total == 0
        assert report.pass_rate == 0.0

    async def test_run_with_failures(self) -> None:
        """EvalSuite.run() correctly reports failures."""

        class FakeAgent:
            async def execute(self, query: str) -> ExecutionResult:
                return _result("always the same")

        agent = FakeAgent()
        suite = EvalSuite("failure-test")
        suite.add_case(
            EvalCase(query="q1", evaluator=ExactMatchEvaluator("always the same"))
        )
        suite.add_case(
            EvalCase(query="q2", evaluator=ExactMatchEvaluator("something else"))
        )

        report = await suite.run(agent)

        assert report.total == 2
        assert report.passed == 1
        assert report.failed == 1
        assert report.pass_rate == 0.5


# ---------------------------------------------------------------------------
# EvalCase dataclass
# ---------------------------------------------------------------------------


class TestEvalCase:
    def test_defaults(self) -> None:
        case = EvalCase(query="test", evaluator=ContainsEvaluator("x"))
        assert case.name is None
        assert case.tags == []

    def test_with_name_and_tags(self) -> None:
        case = EvalCase(
            query="test",
            evaluator=ContainsEvaluator("x"),
            name="my-case",
            tags=["smoke", "fast"],
        )
        assert case.name == "my-case"
        assert case.tags == ["smoke", "fast"]


# ---------------------------------------------------------------------------
# EvalCaseResult dataclass
# ---------------------------------------------------------------------------


class TestEvalCaseResult:
    def test_fields(self) -> None:
        case = EvalCase(query="q", evaluator=ContainsEvaluator("x"))
        result = _result("x marks the spot")
        cr = EvalCaseResult(case=case, passed=True, result=result)
        assert cr.case is case
        assert cr.passed is True
        assert cr.result.content == "x marks the spot"
