from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Callable

from pydantic import BaseModel, Field

from openclaw_sdk.core.types import ExecutionResult

if TYPE_CHECKING:
    from openclaw_sdk.core.client import OpenClawClient


class ConsensusResult(BaseModel):
    """Result from consensus voting."""

    success: bool
    chosen_result: ExecutionResult | None = None
    all_results: dict[str, ExecutionResult] = Field(default_factory=dict)
    votes: dict[str, int] = Field(default_factory=dict)
    agreement_ratio: float = 0.0


class ConsensusGroup:
    """Run the same query through multiple agents and pick the consensus answer.

    Example::

        group = ConsensusGroup(client, ["analyst-1", "analyst-2", "analyst-3"])
        result = await group.vote("What is 2+2?", method="majority")
    """

    def __init__(
        self,
        client: OpenClawClient,
        agent_ids: list[str],
    ) -> None:
        self._client = client
        self._agent_ids = list(agent_ids)

    async def vote(
        self,
        query: str,
        *,
        method: str = "majority",  # "majority" | "unanimous" | "any"
        scorer: Callable[[ExecutionResult], str] | None = None,
    ) -> ConsensusResult:
        """Run query through all agents and determine consensus.

        Args:
            query: The query to execute.
            method: Voting method.

                - ``majority``: More than half of agents must agree.
                - ``unanimous``: All agents must produce the same answer.
                - ``any``: Success if at least one agent succeeds.

            scorer: Function to extract a comparable key from results.
                    Defaults to using the full content string (stripped, lowercased).

        Returns:
            A :class:`ConsensusResult` with voting details.
        """
        if scorer is None:

            def _default_scorer(r: ExecutionResult) -> str:
                return r.content.strip().lower()

            scorer = _default_scorer

        agents = {aid: self._client.get_agent(aid) for aid in self._agent_ids}

        async def run_one(agent_id: str) -> tuple[str, ExecutionResult]:
            result = await agents[agent_id].execute(query)
            return agent_id, result

        pairs = await asyncio.gather(*(run_one(aid) for aid in agents))

        all_results: dict[str, ExecutionResult] = {}
        votes_map: dict[str, list[str]] = {}  # score_key -> [agent_ids]

        for agent_id, result in pairs:
            all_results[agent_id] = result
            key = scorer(result)
            votes_map.setdefault(key, []).append(agent_id)

        # Count votes
        vote_counts = {k: len(v) for k, v in votes_map.items()}
        total = len(all_results)

        if method == "unanimous":
            success = len(votes_map) == 1
        elif method == "any":
            success = any(r.success for r in all_results.values())
        else:  # majority
            success = max(vote_counts.values(), default=0) > total / 2

        # Pick the winning result
        if vote_counts:
            winner_key = max(vote_counts, key=lambda k: vote_counts[k])
            winner_agent = votes_map[winner_key][0]
            chosen = all_results[winner_agent]
            agreement = vote_counts[winner_key] / total if total > 0 else 0.0
        else:
            chosen = None
            agreement = 0.0

        return ConsensusResult(
            success=success,
            chosen_result=chosen,
            all_results=all_results,
            votes=vote_counts,
            agreement_ratio=agreement,
        )
