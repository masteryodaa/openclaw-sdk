"""GoalLoop — iterative agent execution until success or budget exhaustion."""

from __future__ import annotations

import time
from typing import Callable, Protocol

import structlog

from openclaw_sdk.autonomous.models import Budget, Goal, GoalStatus
from openclaw_sdk.autonomous.watchdog import Watchdog, WatchdogAction
from openclaw_sdk.core.types import ExecutionResult

logger = structlog.get_logger(__name__)


class _AgentLike(Protocol):
    """Structural protocol for any object that can execute a query."""

    async def execute(self, query: str) -> ExecutionResult: ...


class GoalLoop:
    """Iterative agent execution loop that runs until a success predicate
    passes or the budget is exhausted.

    Each iteration sends ``goal.description`` to the agent, checks the
    response against the optional *success_predicate*, and updates the
    budget tracking.

    Args:
        agent: An :class:`~openclaw_sdk.core.agent.Agent` (or any object
            satisfying the ``_AgentLike`` protocol).
        goal: The :class:`~openclaw_sdk.autonomous.models.Goal` to pursue.
        budget: The :class:`~openclaw_sdk.autonomous.models.Budget` governing
            resource limits.
        success_predicate: An optional callable ``(ExecutionResult) -> bool``.
            If ``None``, the loop succeeds on the first successful execution.
        on_step: Optional callback invoked after every iteration with the
            step number and :class:`ExecutionResult`.

    Example::

        loop = GoalLoop(agent, goal, budget)
        completed_goal = await loop.run()
        print(completed_goal.status, completed_goal.result)
    """

    def __init__(
        self,
        agent: _AgentLike,
        goal: Goal,
        budget: Budget,
        *,
        success_predicate: Callable[[ExecutionResult], bool] | None = None,
        on_step: Callable[[int, ExecutionResult], None] | None = None,
    ) -> None:
        self._agent = agent
        self._goal = goal
        self._budget = budget
        self._success_predicate = success_predicate
        self._on_step = on_step
        self._watchdog = Watchdog(budget)

    async def run(self) -> Goal:
        """Execute the goal loop and return the updated :class:`Goal`.

        The goal's ``status`` and ``result`` fields are mutated in place.

        Returns:
            The same :class:`Goal` instance with updated status and result.
        """
        self._goal.status = GoalStatus.IN_PROGRESS
        logger.info(
            "goal_loop_start",
            description=self._goal.description,
            max_steps=self._goal.max_steps,
        )

        for step in range(1, self._goal.max_steps + 1):
            # Pre-check budget via watchdog
            action = self._watchdog.check()
            if action == WatchdogAction.STOP:
                logger.warning("goal_loop_budget_exhausted", step=step)
                self._goal.status = GoalStatus.FAILED
                self._goal.result = "Budget exhausted"
                return self._goal

            t0 = time.monotonic()
            try:
                result = await self._agent.execute(self._goal.description)
            except Exception as exc:
                logger.error("goal_loop_execution_error", step=step, error=str(exc))
                self._goal.status = GoalStatus.FAILED
                self._goal.result = f"Execution error: {exc}"
                return self._goal

            elapsed = time.monotonic() - t0

            # Update budget tracking
            self._budget.duration_spent += elapsed
            self._budget.tokens_spent += result.token_usage.total
            self._budget.tool_calls_spent += len(result.tool_calls)

            logger.debug(
                "goal_loop_step",
                step=step,
                success=result.success,
                elapsed_s=round(elapsed, 3),
            )

            if self._on_step is not None:
                self._on_step(step, result)

            # Check for failure
            if not result.success:
                logger.warning("goal_loop_step_failed", step=step)
                continue

            # Check success predicate
            if self._success_predicate is not None:
                if self._success_predicate(result):
                    self._goal.status = GoalStatus.COMPLETED
                    self._goal.result = result.content
                    logger.info("goal_loop_success", step=step)
                    return self._goal
            else:
                # No predicate — succeed on first successful execution
                self._goal.status = GoalStatus.COMPLETED
                self._goal.result = result.content
                logger.info("goal_loop_success", step=step)
                return self._goal

        # Exhausted all steps without success
        self._goal.status = GoalStatus.FAILED
        self._goal.result = (
            f"Max steps ({self._goal.max_steps}) reached without success"
        )
        logger.warning("goal_loop_max_steps", max_steps=self._goal.max_steps)
        return self._goal
