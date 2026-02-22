"""Autonomous agent endpoints — goal creation, goal loops, and budget tracking."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from openclaw_sdk.autonomous import Budget, Goal, GoalLoop, GoalStatus

from . import gateway

router = APIRouter(prefix="/api/autonomous", tags=["autonomous"])

# Track goals and budgets
_goals: list[dict[str, Any]] = []
_budget = Budget(
    max_cost_usd=10.0,
    max_tokens=1_000_000,
    max_duration_seconds=300.0,
    max_tool_calls=100,
)


# -- Request models --


class CreateGoalBody(BaseModel):
    description: str
    max_steps: int = 10
    metadata: dict[str, Any] = {}


class RunGoalBody(BaseModel):
    agent_id: str
    description: str
    max_steps: int = 10
    max_cost_usd: float | None = None
    max_tokens: int | None = None
    max_duration_seconds: float | None = None


class SetBudgetBody(BaseModel):
    max_cost_usd: float | None = None
    max_tokens: int | None = None
    max_duration_seconds: float | None = None
    max_tool_calls: int | None = None


# -- Endpoints --


@router.post("/goals")
async def create_goal(body: CreateGoalBody):
    """Create a new autonomous goal (does not run it)."""
    goal = Goal(
        description=body.description,
        max_steps=body.max_steps,
        metadata=body.metadata,
    )
    goal_data = {
        "description": goal.description,
        "status": goal.status,
        "max_steps": goal.max_steps,
        "metadata": goal.metadata,
        "result": goal.result,
    }
    _goals.append(goal_data)
    return {
        "created": True,
        "goal": goal_data,
        "index": len(_goals) - 1,
    }


@router.get("/goals")
async def list_goals():
    """List all created goals."""
    return {"goals": _goals}


@router.post("/goals/run")
async def run_goal(body: RunGoalBody):
    """Run a goal loop with an agent until success or budget exhaustion."""
    client = await gateway.get_client()
    agent = client.get_agent(body.agent_id)

    goal = Goal(
        description=body.description,
        max_steps=body.max_steps,
    )

    budget = Budget(
        max_cost_usd=body.max_cost_usd or _budget.max_cost_usd,
        max_tokens=body.max_tokens or _budget.max_tokens,
        max_duration_seconds=body.max_duration_seconds or _budget.max_duration_seconds,
        max_tool_calls=_budget.max_tool_calls,
    )

    steps_log: list[dict[str, Any]] = []

    def on_step(step_num: int, result: Any) -> None:
        steps_log.append({
            "step": step_num,
            "success": result.success,
            "content": result.content[:200] if result.content else "",
        })

    loop = GoalLoop(agent, goal, budget, on_step=on_step)

    try:
        completed = await loop.run()
        goal_data = {
            "description": completed.description,
            "status": completed.status,
            "result": completed.result,
            "max_steps": completed.max_steps,
        }
        _goals.append(goal_data)

        return {
            "success": completed.status == GoalStatus.COMPLETED,
            "status": completed.status,
            "result": completed.result,
            "steps_executed": len(steps_log),
            "steps": steps_log,
            "budget": {
                "cost_spent": round(budget.cost_spent, 6),
                "tokens_spent": budget.tokens_spent,
                "duration_spent": round(budget.duration_spent, 2),
                "tool_calls_spent": budget.tool_calls_spent,
                "is_exhausted": budget.is_exhausted,
            },
        }
    except Exception as exc:
        return {"error": str(exc)}


@router.get("/budget")
async def get_budget():
    """Get the current global budget status."""
    return {
        "max_cost_usd": _budget.max_cost_usd,
        "max_tokens": _budget.max_tokens,
        "max_duration_seconds": _budget.max_duration_seconds,
        "max_tool_calls": _budget.max_tool_calls,
        "cost_spent": round(_budget.cost_spent, 6),
        "tokens_spent": _budget.tokens_spent,
        "duration_spent": round(_budget.duration_spent, 2),
        "tool_calls_spent": _budget.tool_calls_spent,
        "is_exhausted": _budget.is_exhausted,
        "remaining_cost": _budget.remaining_cost,
        "remaining_tokens": _budget.remaining_tokens,
    }


@router.post("/budget")
async def set_budget(body: SetBudgetBody):
    """Update the global budget limits."""
    global _budget
    _budget = Budget(
        max_cost_usd=body.max_cost_usd,
        max_tokens=body.max_tokens,
        max_duration_seconds=body.max_duration_seconds,
        max_tool_calls=body.max_tool_calls,
    )
    return {"updated": True, "budget": {
        "max_cost_usd": _budget.max_cost_usd,
        "max_tokens": _budget.max_tokens,
        "max_duration_seconds": _budget.max_duration_seconds,
        "max_tool_calls": _budget.max_tool_calls,
    }}
