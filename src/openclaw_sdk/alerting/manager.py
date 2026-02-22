"""Alert manager that evaluates rules and dispatches alerts to sinks."""
from __future__ import annotations

import time

import structlog

from openclaw_sdk.alerting.models import Alert
from openclaw_sdk.alerting.rules import AlertRule
from openclaw_sdk.alerting.sinks import AlertSink
from openclaw_sdk.core.types import ExecutionResult

logger = structlog.get_logger(__name__)


class AlertManager:
    """Evaluates rules against execution results and dispatches alerts to sinks.

    Supports cooldown periods to prevent alert flooding. Each rule is subject to
    a per-rule cooldown: if the same rule fires again within ``cooldown_seconds``
    of the last alert, the alert is suppressed.

    Uses a builder-style API for fluent configuration::

        manager = (
            AlertManager()
            .add_rule(CostThresholdRule(threshold_usd=0.10))
            .add_sink(LogAlertSink())
            .set_cooldown(30.0)
        )
    """

    def __init__(self) -> None:
        self._rules: list[AlertRule] = []
        self._sinks: list[AlertSink] = []
        self._cooldowns: dict[str, float] = {}
        self._cooldown_seconds: float = 60.0

    def add_rule(self, rule: AlertRule) -> AlertManager:
        """Add a rule to evaluate on each execution result."""
        self._rules.append(rule)
        return self

    def add_sink(self, sink: AlertSink) -> AlertManager:
        """Add a sink for alert delivery."""
        self._sinks.append(sink)
        return self

    def set_cooldown(self, seconds: float) -> AlertManager:
        """Set the per-rule cooldown period in seconds."""
        self._cooldown_seconds = seconds
        return self

    def _is_cooled_down(self, rule_name: str) -> bool:
        """Check whether a rule is still in its cooldown period."""
        last_fired = self._cooldowns.get(rule_name)
        if last_fired is None:
            return False
        return (time.monotonic() - last_fired) < self._cooldown_seconds

    async def evaluate(self, agent_id: str, result: ExecutionResult) -> list[Alert]:
        """Evaluate all rules against the result and dispatch any alerts.

        Returns:
            List of alerts that were actually fired (not suppressed by cooldown).
        """
        fired: list[Alert] = []

        for rule in self._rules:
            try:
                alert = await rule.evaluate(agent_id, result)
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "alert_rule_error", rule=rule.name, error=str(exc)
                )
                continue

            if alert is None:
                continue

            # Apply cooldown
            if self._is_cooled_down(rule.name):
                logger.debug(
                    "alert_suppressed_cooldown",
                    rule=rule.name,
                    cooldown_seconds=self._cooldown_seconds,
                )
                continue

            # Dispatch to all sinks
            self._cooldowns[rule.name] = time.monotonic()
            for sink in self._sinks:
                try:
                    await sink.send(alert)
                except Exception as exc:  # noqa: BLE001
                    logger.error(
                        "alert_sink_error",
                        sink=type(sink).__name__,
                        error=str(exc),
                    )

            fired.append(alert)

        return fired
