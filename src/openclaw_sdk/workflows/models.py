"""Workflow data models — steps, statuses, and results."""
from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class StepStatus(StrEnum):
    """Status of a workflow step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class StepType(StrEnum):
    """Type of a workflow step."""

    AGENT = "agent"
    CONDITION = "condition"
    APPROVAL = "approval"
    TRANSFORM = "transform"


class WorkflowStep(BaseModel):
    """A single step in a workflow.

    Each step has a type that determines how it is executed:

    - **AGENT**: Calls an agent via ``agent_factory`` with the configured
      ``agent_id`` and ``query``.
    - **CONDITION**: Evaluates a condition on the workflow context and
      routes to ``next_on_success`` or ``next_on_failure``.
    - **APPROVAL**: Checks ``auto_approve`` config; in production would
      wait for human approval.
    - **TRANSFORM**: Applies a transformation function or key mapping to
      the workflow context.
    """

    name: str
    step_type: StepType
    config: dict[str, Any] = Field(default_factory=dict)
    status: StepStatus = StepStatus.PENDING
    result: Any = None
    next_on_success: str | None = None
    next_on_failure: str | None = None


class WorkflowResult(BaseModel):
    """Result of a workflow execution.

    Attributes:
        success: Whether the workflow completed without failures.
        steps: All steps with their final statuses and results.
        final_output: The result of the last executed step.
        latency_ms: Total wall-clock time in milliseconds.
    """

    success: bool
    steps: list[WorkflowStep]
    final_output: Any = None
    latency_ms: int = 0
