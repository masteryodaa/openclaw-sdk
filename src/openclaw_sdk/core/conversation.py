from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from openclaw_sdk.core.agent import Agent
    from openclaw_sdk.core.types import ExecutionResult


class Conversation:
    """Multi-turn conversation helper wrapping an :class:`Agent`.

    Tracks local history and provides a clean ``say()`` / ``reset()`` API
    so callers don't need to manage session keys manually.

    Usage::

        async with agent.conversation("session-1") as convo:
            r1 = await convo.say("Hello")
            r2 = await convo.say("Follow-up question")
            print(convo.turns)  # 2

    Or without context manager::

        convo = agent.conversation()
        result = await convo.say("Hi there")
    """

    def __init__(self, agent: Agent, session_name: str = "main") -> None:
        self._agent = agent
        self._session_name = session_name
        self._history: list[tuple[str, str]] = []  # (query, response)

    async def say(self, message: str, **kwargs: Any) -> ExecutionResult:
        """Send *message* to the agent and record the exchange.

        Args:
            message: The user message to send.
            **kwargs: Forwarded to :meth:`Agent.execute`.

        Returns:
            The :class:`~openclaw_sdk.core.types.ExecutionResult`.
        """
        result = await self._agent.execute(message, **kwargs)
        self._history.append((message, result.content))
        return result

    async def get_history(self) -> list[dict[str, Any]]:
        """Fetch server-side conversation history from the gateway.

        Returns:
            List of message dicts from ``chat.history``.
        """
        return await self._agent._client.gateway.chat_history(
            self._agent.session_key
        )

    async def reset(self) -> None:
        """Clear both server-side memory and local history."""
        await self._agent.reset_memory()
        self._history.clear()

    @property
    def turns(self) -> int:
        """Number of completed exchanges."""
        return len(self._history)

    @property
    def history(self) -> list[tuple[str, str]]:
        """Local (query, response) history — read-only copy."""
        return list(self._history)

    async def __aenter__(self) -> Conversation:
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass
