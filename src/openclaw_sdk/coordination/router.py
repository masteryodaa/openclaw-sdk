from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from openclaw_sdk.core.types import ExecutionResult

if TYPE_CHECKING:
    from openclaw_sdk.core.client import OpenClawClient


class AgentRouter:
    """Route queries to different agents based on content.

    Example::

        router = AgentRouter(client)
        router.add_route(lambda q: "code" in q.lower(), "code-reviewer")
        router.add_route(lambda q: "data" in q.lower(), "data-analyst")
        router.set_default("assistant")
        result = await router.route("Review this code snippet")
    """

    def __init__(self, client: OpenClawClient) -> None:
        self._client = client
        self._routes: list[tuple[Callable[[str], bool], str]] = []
        self._default_agent: str | None = None

    def add_route(
        self,
        condition: Callable[[str], bool],
        agent_id: str,
    ) -> AgentRouter:
        """Add a routing rule.

        Args:
            condition: A callable that takes a query string and returns
                       ``True`` if this route matches.
            agent_id: The agent to route to when condition matches.

        Returns:
            ``self`` for fluent chaining.
        """
        self._routes.append((condition, agent_id))
        return self

    def set_default(self, agent_id: str) -> AgentRouter:
        """Set the default agent for unmatched queries.

        Args:
            agent_id: The fallback agent identifier.

        Returns:
            ``self`` for fluent chaining.
        """
        self._default_agent = agent_id
        return self

    def resolve(self, query: str) -> str:
        """Determine which agent should handle the query.

        Args:
            query: The user query.

        Returns:
            The matched agent identifier.

        Raises:
            ValueError: If no route matches and no default agent is set.
        """
        for condition, agent_id in self._routes:
            if condition(query):
                return agent_id
        if self._default_agent:
            return self._default_agent
        raise ValueError(f"No route matched query and no default agent set: {query!r}")

    async def route(self, query: str) -> ExecutionResult:
        """Route the query to the matching agent and execute.

        Args:
            query: The user query to route and execute.

        Returns:
            An :class:`~openclaw_sdk.core.types.ExecutionResult` from the
            matched agent.
        """
        agent_id = self.resolve(query)
        agent = self._client.get_agent(agent_id)
        return await agent.execute(query)
