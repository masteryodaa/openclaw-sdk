"""Autonomous agent models: goals, budgets, and status tracking."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class GoalStatus(StrEnum):
    """Status of an autonomous goal."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Goal(BaseModel):
    """An autonomous goal that an agent should accomplish.

    Goals can be hierarchical — a goal may contain ``sub_goals`` that
    must be completed as part of the parent goal.

    Attributes:
        description: Natural-language description of what to achieve.
        status: Current status of the goal (default :attr:`GoalStatus.PENDING`).
        sub_goals: Optional child goals for decomposition.
        max_steps: Maximum number of execution iterations (default 10).
        result: The final result string once the goal completes (or fails).
        metadata: Arbitrary key/value metadata attached to the goal.
    """

    description: str
    status: GoalStatus = GoalStatus.PENDING
    sub_goals: list[Goal] = Field(default_factory=list)
    max_steps: int = 10
    result: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Budget(BaseModel):
    """Resource budget for autonomous execution.

    Each limit field is optional — ``None`` means unlimited for that
    dimension.  The ``*_spent`` fields track consumption during execution.

    Properties:
        is_exhausted: ``True`` when any non-None limit has been reached or exceeded.
        remaining_cost: Remaining cost in USD, or ``None`` if unlimited.
        remaining_tokens: Remaining tokens, or ``None`` if unlimited.
    """

    max_cost_usd: float | None = None
    max_tokens: int | None = None
    max_duration_seconds: float | None = None
    max_tool_calls: int | None = None

    cost_spent: float = 0.0
    tokens_spent: int = 0
    duration_spent: float = 0.0
    tool_calls_spent: int = 0

    @property
    def is_exhausted(self) -> bool:
        """Return ``True`` if any configured limit has been reached."""
        if self.max_cost_usd is not None and self.cost_spent >= self.max_cost_usd:
            return True
        if self.max_tokens is not None and self.tokens_spent >= self.max_tokens:
            return True
        if (
            self.max_duration_seconds is not None
            and self.duration_spent >= self.max_duration_seconds
        ):
            return True
        if (
            self.max_tool_calls is not None
            and self.tool_calls_spent >= self.max_tool_calls
        ):
            return True
        return False

    @property
    def remaining_cost(self) -> float | None:
        """Remaining cost in USD, or ``None`` if no cost limit is set."""
        if self.max_cost_usd is None:
            return None
        return max(0.0, self.max_cost_usd - self.cost_spent)

    @property
    def remaining_tokens(self) -> int | None:
        """Remaining tokens, or ``None`` if no token limit is set."""
        if self.max_tokens is None:
            return None
        return max(0, self.max_tokens - self.tokens_spent)
