"""Alert rules that evaluate execution results and optionally produce alerts."""
from __future__ import annotations

from abc import ABC, abstractmethod

from openclaw_sdk.alerting.models import Alert, AlertSeverity
from openclaw_sdk.core.types import ExecutionResult


class AlertRule(ABC):
    """Base class for alert rules.

    Subclass and implement :meth:`evaluate` to inspect an
    :class:`ExecutionResult` and optionally return an :class:`Alert`.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name for this rule."""
        ...

    @abstractmethod
    async def evaluate(self, agent_id: str, result: ExecutionResult) -> Alert | None:
        """Evaluate the result and return an alert if the condition is met."""
        ...


class CostThresholdRule(AlertRule):
    """Fires when the estimated execution cost exceeds a USD threshold.

    Cost is calculated from token usage: ``(input + output) / 1_000_000 * rate``.
    A simplified default rate of $10/M tokens is used. Override ``rate_per_million``
    for different pricing.
    """

    def __init__(
        self,
        threshold_usd: float,
        severity: AlertSeverity = AlertSeverity.WARNING,
        *,
        rate_per_million: float = 10.0,
    ) -> None:
        self._threshold_usd = threshold_usd
        self._severity = severity
        self._rate_per_million = rate_per_million

    @property
    def name(self) -> str:
        return "cost_threshold"

    async def evaluate(self, agent_id: str, result: ExecutionResult) -> Alert | None:
        total_tokens = result.token_usage.input + result.token_usage.output
        estimated_cost = (total_tokens / 1_000_000) * self._rate_per_million
        if estimated_cost > self._threshold_usd:
            return Alert(
                severity=self._severity,
                title="Cost threshold exceeded",
                message=(
                    f"Estimated cost ${estimated_cost:.4f} exceeds "
                    f"threshold ${self._threshold_usd:.4f}"
                ),
                agent_id=agent_id,
                rule_name=self.name,
                metadata={"estimated_cost_usd": estimated_cost, "threshold_usd": self._threshold_usd},
            )
        return None


class LatencyThresholdRule(AlertRule):
    """Fires when execution latency exceeds the configured threshold in milliseconds."""

    def __init__(
        self,
        threshold_ms: int,
        severity: AlertSeverity = AlertSeverity.WARNING,
    ) -> None:
        self._threshold_ms = threshold_ms
        self._severity = severity

    @property
    def name(self) -> str:
        return "latency_threshold"

    async def evaluate(self, agent_id: str, result: ExecutionResult) -> Alert | None:
        if result.latency_ms > self._threshold_ms:
            return Alert(
                severity=self._severity,
                title="Latency threshold exceeded",
                message=(
                    f"Latency {result.latency_ms}ms exceeds "
                    f"threshold {self._threshold_ms}ms"
                ),
                agent_id=agent_id,
                rule_name=self.name,
                metadata={"latency_ms": result.latency_ms, "threshold_ms": self._threshold_ms},
            )
        return None


class ErrorRateRule(AlertRule):
    """Fires when the error rate exceeds a threshold within a sliding window.

    Maintains a fixed-size window of recent results (True = success, False = failure).
    The alert fires when the failure rate within the window exceeds ``threshold``.
    """

    def __init__(
        self,
        threshold: float = 0.5,
        window_size: int = 10,
        severity: AlertSeverity = AlertSeverity.CRITICAL,
    ) -> None:
        self._threshold = threshold
        self._window_size = window_size
        self._severity = severity
        self._results: list[bool] = []

    @property
    def name(self) -> str:
        return "error_rate"

    async def evaluate(self, agent_id: str, result: ExecutionResult) -> Alert | None:
        self._results.append(result.success)
        # Keep only the last window_size results
        if len(self._results) > self._window_size:
            self._results = self._results[-self._window_size :]

        # Only evaluate when we have a full window
        if len(self._results) < self._window_size:
            return None

        failure_count = sum(1 for r in self._results if not r)
        error_rate = failure_count / len(self._results)
        if error_rate > self._threshold:
            return Alert(
                severity=self._severity,
                title="Error rate threshold exceeded",
                message=(
                    f"Error rate {error_rate:.1%} exceeds "
                    f"threshold {self._threshold:.1%} "
                    f"(window size: {self._window_size})"
                ),
                agent_id=agent_id,
                rule_name=self.name,
                metadata={
                    "error_rate": error_rate,
                    "threshold": self._threshold,
                    "window_size": self._window_size,
                },
            )
        return None


class ConsecutiveFailureRule(AlertRule):
    """Fires after N consecutive failures. Resets on success."""

    def __init__(
        self,
        threshold: int = 3,
        severity: AlertSeverity = AlertSeverity.CRITICAL,
    ) -> None:
        self._threshold = threshold
        self._severity = severity
        self._consecutive_failures: int = 0

    @property
    def name(self) -> str:
        return "consecutive_failure"

    async def evaluate(self, agent_id: str, result: ExecutionResult) -> Alert | None:
        if result.success:
            self._consecutive_failures = 0
            return None

        self._consecutive_failures += 1
        if self._consecutive_failures >= self._threshold:
            return Alert(
                severity=self._severity,
                title="Consecutive failures threshold reached",
                message=(
                    f"{self._consecutive_failures} consecutive failures "
                    f"(threshold: {self._threshold})"
                ),
                agent_id=agent_id,
                rule_name=self.name,
                metadata={
                    "consecutive_failures": self._consecutive_failures,
                    "threshold": self._threshold,
                },
            )
        return None
