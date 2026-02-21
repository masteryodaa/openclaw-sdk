from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from openclaw_sdk.core.types import ExecutionResult

if TYPE_CHECKING:
    from openclaw_sdk.core.client import OpenClawClient


class SupervisorResult(BaseModel):
    """Result from a supervised multi-agent execution."""

    success: bool
    final_result: ExecutionResult | None = None
    worker_results: dict[str, ExecutionResult] = Field(default_factory=dict)
    delegations: list[str] = Field(default_factory=list)
    latency_ms: int = 0


class Supervisor:
    """Coordinates multiple worker agents under a supervisor pattern.

    The supervisor dispatches tasks to workers, collects results,
    and can synthesize a final response.

    Example::

        supervisor = Supervisor(client, supervisor_agent_id="manager")
        supervisor.add_worker("researcher", description="Research tasks")
        supervisor.add_worker("writer", description="Writing tasks")
        result = await supervisor.delegate(
            "Research AI trends and write a report",
            strategy="sequential",
        )
    """

    def __init__(
        self,
        client: OpenClawClient,
        supervisor_agent_id: str | None = None,
    ) -> None:
        self._client = client
        self._supervisor_id = supervisor_agent_id
        self._workers: dict[str, str] = {}  # agent_id -> description

    def add_worker(self, agent_id: str, description: str = "") -> Supervisor:
        """Register a worker agent.

        Args:
            agent_id: The worker agent's identifier.
            description: Human-readable description of the worker's purpose.

        Returns:
            ``self`` for fluent chaining.
        """
        self._workers[agent_id] = description
        return self

    async def delegate(
        self,
        task: str,
        *,
        strategy: str = "sequential",  # "sequential" | "parallel" | "round-robin"
        max_rounds: int = 1,
    ) -> SupervisorResult:
        """Delegate a task to worker agents.

        Strategies:
            - ``sequential``: Workers execute in registration order; each sees
              previous results as context.
            - ``parallel``: All workers execute concurrently on the same task.
            - ``round-robin``: Workers are tried in order; first success wins.

        Args:
            task: The task description to delegate.
            strategy: Execution strategy (default ``"sequential"``).
            max_rounds: Number of full passes through workers (sequential only).

        Returns:
            A :class:`SupervisorResult` with aggregated outcomes.
        """
        t0 = time.monotonic()

        if strategy == "parallel":
            result = await self._run_parallel(task)
        elif strategy == "round-robin":
            result = await self._run_round_robin(task)
        else:
            result = await self._run_sequential(task, max_rounds)

        result.latency_ms = int((time.monotonic() - t0) * 1000)
        return result

    async def _run_sequential(self, task: str, max_rounds: int) -> SupervisorResult:
        """Workers execute in order, accumulating context."""
        worker_results: dict[str, ExecutionResult] = {}
        delegations: list[str] = []
        context = task

        for _ in range(max_rounds):
            for agent_id in self._workers:
                agent = self._client.get_agent(agent_id)
                result = await agent.execute(context)
                worker_results[agent_id] = result
                delegations.append(agent_id)
                if result.success:
                    context = (
                        f"Previous result from {agent_id}: {result.content}\n\n"
                        f"Original task: {task}"
                    )

        # Last result is the final
        final = list(worker_results.values())[-1] if worker_results else None
        return SupervisorResult(
            success=final.success if final else False,
            final_result=final,
            worker_results=worker_results,
            delegations=delegations,
        )

    async def _run_parallel(self, task: str) -> SupervisorResult:
        """All workers execute concurrently."""
        agents = {aid: self._client.get_agent(aid) for aid in self._workers}

        async def run_one(agent_id: str) -> tuple[str, ExecutionResult]:
            result = await agents[agent_id].execute(task)
            return agent_id, result

        pairs = await asyncio.gather(
            *(run_one(aid) for aid in agents),
            return_exceptions=True,
        )

        worker_results: dict[str, ExecutionResult] = {}
        delegations: list[str] = []
        for pair in pairs:
            if isinstance(pair, BaseException):
                continue
            agent_id, result = pair
            worker_results[agent_id] = result
            delegations.append(agent_id)

        final = list(worker_results.values())[-1] if worker_results else None
        return SupervisorResult(
            success=final.success if final else False,
            final_result=final,
            worker_results=worker_results,
            delegations=delegations,
        )

    async def _run_round_robin(self, task: str) -> SupervisorResult:
        """Try workers in order, first success wins."""
        worker_results: dict[str, ExecutionResult] = {}
        delegations: list[str] = []

        for agent_id in self._workers:
            agent = self._client.get_agent(agent_id)
            result = await agent.execute(task)
            worker_results[agent_id] = result
            delegations.append(agent_id)
            if result.success:
                return SupervisorResult(
                    success=True,
                    final_result=result,
                    worker_results=worker_results,
                    delegations=delegations,
                )

        final = list(worker_results.values())[-1] if worker_results else None
        return SupervisorResult(
            success=False,
            final_result=final,
            worker_results=worker_results,
            delegations=delegations,
        )
