"""Workflow engine — branching state machine with conditions and approvals.

Complements the linear :class:`~openclaw_sdk.pipeline.pipeline.Pipeline` with
branching, conditional routing, human approvals, and context transformations.
"""
from __future__ import annotations

import time
from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Callable, Protocol, runtime_checkable

import structlog

from openclaw_sdk.workflows.models import (
    StepStatus,
    StepType,
    WorkflowResult,
    WorkflowStep,
)

if TYPE_CHECKING:
    from openclaw_sdk.core.types import ExecutionResult

logger = structlog.get_logger(__name__)


def _now_ms() -> int:
    return int(time.monotonic() * 1000)


@runtime_checkable
class _AgentLike(Protocol):
    """Minimal agent interface required by the workflow engine."""

    async def execute(self, query: str) -> ExecutionResult: ...


class Workflow:
    """Branching state-machine workflow engine.

    Unlike the linear :class:`~openclaw_sdk.pipeline.pipeline.Pipeline`, a
    ``Workflow`` supports:

    - **Conditional branching**: route to different steps based on context values.
    - **Human approvals**: gate execution on approval (auto or manual).
    - **Context transforms**: modify the shared context dict between steps.
    - **Named step navigation**: steps can specify ``next_on_success`` /
      ``next_on_failure`` to jump to arbitrary steps.

    Args:
        name: Human-readable workflow name.
        steps: Ordered list of :class:`WorkflowStep` definitions.

    Example::

        wf = Workflow("review", [
            WorkflowStep(name="review", step_type=StepType.AGENT,
                         config={"agent_id": "reviewer", "query": "Review: {doc}"}),
            WorkflowStep(name="check", step_type=StepType.CONDITION,
                         config={"key": "review_passed", "operator": "eq", "value": True},
                         next_on_success="done", next_on_failure="revise"),
            WorkflowStep(name="revise", step_type=StepType.AGENT,
                         config={"agent_id": "author", "query": "Revise based on: {review}"}),
        ])
        result = await wf.run({"doc": "my document"}, agent_factory=factory)
    """

    def __init__(self, name: str, steps: list[WorkflowStep]) -> None:
        self.name = name
        self._steps: OrderedDict[str, WorkflowStep] = OrderedDict()
        for step in steps:
            self._steps[step.name] = step.model_copy(deep=True)

    def __repr__(self) -> str:
        return f"Workflow(name={self.name!r}, steps={len(self._steps)})"

    @property
    def steps(self) -> list[WorkflowStep]:
        """Return a list of all steps in order."""
        return list(self._steps.values())

    async def run(
        self,
        context: dict[str, Any],
        *,
        agent_factory: Callable[[str], _AgentLike] | None = None,
    ) -> WorkflowResult:
        """Execute the workflow.

        Steps are executed in insertion order unless a step's
        ``next_on_success`` or ``next_on_failure`` redirects execution
        to a different named step.

        Args:
            context: Mutable dict shared across all steps. Step results
                are stored here under the step's name.
            agent_factory: Callable that takes an ``agent_id`` string and
                returns an agent-like object with an ``execute(query)``
                method. Required when the workflow contains AGENT steps.

        Returns:
            A :class:`WorkflowResult` with the outcome of every step.
        """
        start_ms = _now_ms()
        # Reset all steps to PENDING
        for step in self._steps.values():
            step.status = StepStatus.PENDING
            step.result = None

        # Handle empty workflow
        if not self._steps:
            return WorkflowResult(
                success=True,
                steps=[],
                final_output=None,
                latency_ms=_now_ms() - start_ms,
            )

        step_names = list(self._steps.keys())
        current_index = 0
        final_output: Any = None
        success = True

        while current_index < len(step_names):
            step_name = step_names[current_index]
            step = self._steps[step_name]

            # Skip steps already completed (e.g. jumped past)
            if step.status in (StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.SKIPPED):
                current_index += 1
                continue

            step.status = StepStatus.RUNNING
            logger.debug(
                "workflow step started",
                workflow=self.name,
                step=step.name,
                step_type=step.step_type,
            )

            try:
                step_succeeded = await self._execute_step(
                    step, context, agent_factory
                )
            except Exception as exc:
                step.status = StepStatus.FAILED
                step.result = str(exc)
                logger.error(
                    "workflow step failed",
                    workflow=self.name,
                    step=step.name,
                    error=str(exc),
                )
                success = False
                final_output = step.result
                # Follow failure branch if specified
                if step.next_on_failure and step.next_on_failure in self._steps:
                    next_idx = step_names.index(step.next_on_failure)
                    current_index = next_idx
                    continue
                break

            if step_succeeded:
                step.status = StepStatus.COMPLETED
                final_output = step.result
                logger.debug(
                    "workflow step completed",
                    workflow=self.name,
                    step=step.name,
                )
                # Follow success branch if specified
                if step.next_on_success and step.next_on_success in self._steps:
                    next_idx = step_names.index(step.next_on_success)
                    current_index = next_idx
                    continue
            else:
                step.status = StepStatus.FAILED
                final_output = step.result
                success = False
                logger.debug(
                    "workflow step failed",
                    workflow=self.name,
                    step=step.name,
                )
                # Follow failure branch if specified
                if step.next_on_failure and step.next_on_failure in self._steps:
                    next_idx = step_names.index(step.next_on_failure)
                    current_index = next_idx
                    continue
                break

            current_index += 1

        return WorkflowResult(
            success=success,
            steps=list(self._steps.values()),
            final_output=final_output,
            latency_ms=_now_ms() - start_ms,
        )

    async def _execute_step(
        self,
        step: WorkflowStep,
        context: dict[str, Any],
        agent_factory: Callable[[str], _AgentLike] | None,
    ) -> bool:
        """Execute a single step and return True on success.

        The step's ``result`` field is set as a side-effect. Results are
        also stored in *context* under the step's name.
        """
        if step.step_type == StepType.AGENT:
            return await self._execute_agent_step(step, context, agent_factory)
        elif step.step_type == StepType.CONDITION:
            return self._execute_condition_step(step, context)
        elif step.step_type == StepType.APPROVAL:
            return self._execute_approval_step(step, context)
        elif step.step_type == StepType.TRANSFORM:
            return self._execute_transform_step(step, context)
        else:
            step.result = f"Unknown step type: {step.step_type}"
            return False

    async def _execute_agent_step(
        self,
        step: WorkflowStep,
        context: dict[str, Any],
        agent_factory: Callable[[str], _AgentLike] | None,
    ) -> bool:
        """Execute an AGENT step: call an agent and store its result."""
        if agent_factory is None:
            step.result = "No agent_factory provided for AGENT step"
            return False

        agent_id = step.config.get("agent_id", "")
        query_template = step.config.get("query", "")

        # Format query with context values (safe formatting)
        try:
            query = query_template.format(**context)
        except KeyError:
            # Fall back to partial formatting — leave missing keys as-is
            query = query_template

        agent = agent_factory(agent_id)
        result = await agent.execute(query)

        step.result = result.content
        context[step.name] = result.content
        return result.success

    def _execute_condition_step(
        self,
        step: WorkflowStep,
        context: dict[str, Any],
    ) -> bool:
        """Evaluate a CONDITION step against the context.

        Config format::

            {"key": "score", "operator": "gt", "value": 0.5}

        Supported operators: ``eq``, ``ne``, ``gt``, ``gte``, ``lt``,
        ``lte``, ``in``, ``contains``.
        """
        key = step.config.get("key", "")
        operator = step.config.get("operator", "eq")
        expected = step.config.get("value")

        actual = context.get(key)
        step.result = actual

        result = self._evaluate_condition(actual, operator, expected)
        context[step.name] = result
        return result

    @staticmethod
    def _evaluate_condition(
        actual: Any, operator: str, expected: Any
    ) -> bool:
        """Compare *actual* against *expected* using *operator*."""
        if operator == "eq":
            return bool(actual == expected)
        elif operator == "ne":
            return bool(actual != expected)
        elif operator == "gt":
            return bool(actual is not None and actual > expected)
        elif operator == "gte":
            return bool(actual is not None and actual >= expected)
        elif operator == "lt":
            return bool(actual is not None and actual < expected)
        elif operator == "lte":
            return bool(actual is not None and actual <= expected)
        elif operator == "in":
            return bool(actual in expected) if expected is not None else False
        elif operator == "contains":
            if isinstance(actual, str) and isinstance(expected, str):
                return expected in actual
            return False
        return False

    def _execute_approval_step(
        self,
        step: WorkflowStep,
        context: dict[str, Any],
    ) -> bool:
        """Execute an APPROVAL step.

        In production, this would wait for human approval. For SDK use,
        it checks ``auto_approve`` in the step config.
        """
        auto_approve = step.config.get("auto_approve", False)
        step.result = auto_approve
        context[step.name] = auto_approve
        return bool(auto_approve)

    def _execute_transform_step(
        self,
        step: WorkflowStep,
        context: dict[str, Any],
    ) -> bool:
        """Execute a TRANSFORM step on the context.

        If ``step.config["transform"]`` is callable, it is invoked with
        the context dict and its return value (if a dict) is merged back.

        If ``step.config["mapping"]`` is a dict, keys in the context are
        renamed according to the mapping ``{old_key: new_key}``.
        """
        transform = step.config.get("transform")
        if callable(transform):
            result = transform(context)
            if isinstance(result, dict):
                context.update(result)
            step.result = result
            context[step.name] = result
            return True

        mapping: dict[str, str] | None = step.config.get("mapping")
        if isinstance(mapping, dict):
            for old_key, new_key in mapping.items():
                if old_key in context:
                    context[new_key] = context[old_key]
            step.result = mapping
            context[step.name] = mapping
            return True

        # No transform or mapping — pass through
        step.result = None
        context[step.name] = None
        return True
