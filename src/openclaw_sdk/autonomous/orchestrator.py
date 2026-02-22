"""Orchestrator — manages goal execution across multiple agents."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

import structlog
from pydantic import BaseModel, Field

from openclaw_sdk.autonomous.goal_loop import GoalLoop
from openclaw_sdk.autonomous.models import Budget, Goal, GoalStatus
from openclaw_sdk.core.types import ExecutionResult

if TYPE_CHECKING:
    from openclaw_sdk.core.client import OpenClawClient

logger = structlog.get_logger(__name__)


class AgentCapability(BaseModel):
    """Describes what an agent can do for routing purposes.

    Attributes:
        agent_id: Unique agent identifier.
        description: Human-readable description of the agent's purpose.
        skills: List of skill keywords for matching against goals.
    """

    agent_id: str
    description: str = ""
    skills: list[str] = Field(default_factory=list)


class Orchestrator:
    """Manages goal execution across a pool of registered agents.

    The orchestrator maintains a registry of agent capabilities and routes
    goals to the best-matching agent using simple keyword overlap between
    the goal description and agent skills.

    Example::

        orch = Orchestrator(client)
        orch.register_agent("researcher", "Deep research", ["research", "analysis"])
        orch.register_agent("writer", "Content writing", ["writing", "editing"])
        goal = Goal(description="Research AI safety papers")
        result = await orch.execute_goal(goal, Budget(max_tokens=10000))
    """

    def __init__(self, client: "OpenClawClient") -> None:
        self._client = client
        self._agents: dict[str, AgentCapability] = {}

    def register_agent(
        self,
        agent_id: str,
        description: str = "",
        skills: list[str] | None = None,
    ) -> None:
        """Register an agent's capabilities.

        Args:
            agent_id: Unique agent identifier.
            description: Human-readable description of the agent.
            skills: List of skill keywords for routing.
        """
        cap = AgentCapability(
            agent_id=agent_id,
            description=description,
            skills=skills or [],
        )
        self._agents[agent_id] = cap
        logger.debug("orchestrator_register", agent_id=agent_id, skills=cap.skills)

    def route_goal(self, goal: Goal) -> str | None:
        """Find the best agent for a goal based on skill keyword overlap.

        Scoring: each agent skill is checked against the goal description
        (case-insensitive substring match).  The agent with the highest
        number of matching skills wins.

        Args:
            goal: The goal to route.

        Returns:
            The ``agent_id`` of the best match, or ``None`` if no agent
            has any matching skills.
        """
        if not self._agents:
            return None

        description_lower = goal.description.lower()
        best_id: str | None = None
        best_score = 0

        for agent_id, cap in self._agents.items():
            score = sum(1 for skill in cap.skills if skill.lower() in description_lower)
            if score > best_score:
                best_score = score
                best_id = agent_id

        if best_id is not None:
            logger.debug(
                "orchestrator_route",
                goal=goal.description[:80],
                agent_id=best_id,
                score=best_score,
            )
        return best_id

    async def execute_goal(
        self,
        goal: Goal,
        budget: Budget,
        *,
        agent_override: str | None = None,
        success_predicate: Callable[[ExecutionResult], bool] | None = None,
    ) -> Goal:
        """Route a goal to an agent and execute it.

        If *agent_override* is provided, it is used directly.  Otherwise the
        orchestrator routes the goal to the best-matching agent.

        Args:
            goal: The goal to execute.
            budget: Resource budget for the execution.
            agent_override: Optional explicit agent ID (bypasses routing).
            success_predicate: Optional predicate passed to
                :class:`~openclaw_sdk.autonomous.goal_loop.GoalLoop`.

        Returns:
            The updated :class:`~openclaw_sdk.autonomous.models.Goal` after
            execution completes (or fails).

        Raises:
            ValueError: If no agent can be determined (no override and no
                routing match).
        """
        agent_id = agent_override or self.route_goal(goal)
        if agent_id is None:
            goal.status = GoalStatus.FAILED
            goal.result = "No suitable agent found"
            logger.warning("orchestrator_no_agent", goal=goal.description[:80])
            raise ValueError(
                f"No agent found for goal: {goal.description!r}. "
                "Register agents with matching skills or use agent_override."
            )

        logger.info(
            "orchestrator_execute",
            goal=goal.description[:80],
            agent_id=agent_id,
        )

        agent = self._client.get_agent(agent_id)
        loop = GoalLoop(
            agent,
            goal,
            budget,
            success_predicate=success_predicate,
        )
        return await loop.run()
