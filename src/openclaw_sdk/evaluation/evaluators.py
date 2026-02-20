"""Built-in evaluators for agent response quality."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod

from openclaw_sdk.core.types import ExecutionResult


class Evaluator(ABC):
    """Base class for all evaluators."""

    @abstractmethod
    def evaluate(self, result: ExecutionResult) -> bool:
        """Evaluate an execution result. Returns True if the result passes."""
        ...


class ContainsEvaluator(Evaluator):
    """Check whether the result content contains an expected substring."""

    def __init__(self, expected: str, case_sensitive: bool = False) -> None:
        self._expected = expected
        self._case_sensitive = case_sensitive

    def evaluate(self, result: ExecutionResult) -> bool:
        content = result.content
        expected = self._expected
        if not self._case_sensitive:
            content = content.lower()
            expected = expected.lower()
        return expected in content


class ExactMatchEvaluator(Evaluator):
    """Check whether the result content exactly matches an expected string."""

    def __init__(self, expected: str, strip: bool = True) -> None:
        self._expected = expected
        self._strip = strip

    def evaluate(self, result: ExecutionResult) -> bool:
        content = result.content.strip() if self._strip else result.content
        expected = self._expected.strip() if self._strip else self._expected
        return content == expected


class RegexEvaluator(Evaluator):
    """Check whether the result content matches a regular expression pattern."""

    def __init__(self, pattern: str) -> None:
        self._pattern = re.compile(pattern)

    def evaluate(self, result: ExecutionResult) -> bool:
        return bool(self._pattern.search(result.content))


class LengthEvaluator(Evaluator):
    """Check whether the result content length falls within bounds."""

    def __init__(self, min_length: int = 0, max_length: int | None = None) -> None:
        self._min = min_length
        self._max = max_length

    def evaluate(self, result: ExecutionResult) -> bool:
        length = len(result.content)
        if length < self._min:
            return False
        if self._max is not None and length > self._max:
            return False
        return True
