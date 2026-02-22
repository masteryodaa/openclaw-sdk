"""Watchdog — safety constraints checker for autonomous execution."""

from __future__ import annotations

from enum import StrEnum

import structlog

from openclaw_sdk.autonomous.models import Budget

logger = structlog.get_logger(__name__)

_WARN_THRESHOLD = 0.80  # 80 % of any limit triggers a warning


class WatchdogAction(StrEnum):
    """Action recommended by the watchdog after checking constraints."""

    CONTINUE = "continue"
    WARN = "warn"
    STOP = "stop"


class Watchdog:
    """Safety constraints checker for autonomous goal loops.

    Monitors a :class:`~openclaw_sdk.autonomous.models.Budget` and returns
    an action indicating whether execution should continue, warn, or stop.

    Example::

        watchdog = Watchdog(budget)
        action = watchdog.check()
        if action == WatchdogAction.STOP:
            break
    """

    def __init__(self, budget: Budget) -> None:
        self._budget = budget

    def check(self) -> WatchdogAction:
        """Check the budget and return the recommended action.

        Returns:
            - :attr:`WatchdogAction.STOP` if the budget is exhausted.
            - :attr:`WatchdogAction.WARN` if more than 80 % of any limit is used.
            - :attr:`WatchdogAction.CONTINUE` otherwise.
        """
        if self._budget.is_exhausted:
            logger.warning(
                "watchdog_stop",
                cost_spent=self._budget.cost_spent,
                tokens_spent=self._budget.tokens_spent,
                duration_spent=self._budget.duration_spent,
                tool_calls_spent=self._budget.tool_calls_spent,
            )
            return WatchdogAction.STOP

        if self._any_over_threshold():
            logger.info(
                "watchdog_warn",
                cost_spent=self._budget.cost_spent,
                tokens_spent=self._budget.tokens_spent,
                duration_spent=self._budget.duration_spent,
                tool_calls_spent=self._budget.tool_calls_spent,
            )
            return WatchdogAction.WARN

        return WatchdogAction.CONTINUE

    def _any_over_threshold(self) -> bool:
        """Return ``True`` if any non-None limit is over 80 % consumed."""
        b = self._budget

        if b.max_cost_usd is not None and b.max_cost_usd > 0:
            if b.cost_spent / b.max_cost_usd >= _WARN_THRESHOLD:
                return True

        if b.max_tokens is not None and b.max_tokens > 0:
            if b.tokens_spent / b.max_tokens >= _WARN_THRESHOLD:
                return True

        if b.max_duration_seconds is not None and b.max_duration_seconds > 0:
            if b.duration_spent / b.max_duration_seconds >= _WARN_THRESHOLD:
                return True

        if b.max_tool_calls is not None and b.max_tool_calls > 0:
            if b.tool_calls_spent / b.max_tool_calls >= _WARN_THRESHOLD:
                return True

        return False
