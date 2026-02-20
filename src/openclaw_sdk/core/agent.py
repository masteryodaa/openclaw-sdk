from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any, AsyncIterator

from openclaw_sdk.callbacks.handler import CallbackHandler, CompositeCallbackHandler
from openclaw_sdk.core.constants import EventType
from openclaw_sdk.core.exceptions import AgentExecutionError, OpenClawError
from openclaw_sdk.core.exceptions import TimeoutError as OcTimeoutError
from openclaw_sdk.core.config import ExecutionOptions
from openclaw_sdk.core.types import ExecutionResult, StreamEvent

if TYPE_CHECKING:
    from openclaw_sdk.core.client import OpenClawClient


class Agent:
    """Represents a single OpenClaw agent and exposes execution methods.

    Obtain via :meth:`~openclaw_sdk.core.client.OpenClawClient.get_agent`::

        agent = client.get_agent("research-bot")
        result = await agent.execute("Summarise recent AI papers")
        print(result.content)

    The *session_key* sent to the gateway is ``"agent:{agent_id}:{session_name}"``.
    """

    def __init__(
        self,
        client: "OpenClawClient",
        agent_id: str,
        session_name: str = "main",
    ) -> None:
        self._client = client
        self.agent_id = agent_id
        self.session_name = session_name

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #

    @property
    def session_key(self) -> str:
        """Gateway session key for this agent, e.g. ``"agent:main:main"``."""
        return f"agent:{self.agent_id}:{self.session_name}"

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    async def execute(
        self,
        query: str,
        options: ExecutionOptions | None = None,
        callbacks: list[CallbackHandler] | None = None,
        idempotency_key: str | None = None,
    ) -> ExecutionResult:
        """Send *query* to the agent and return the final result.

        For WebSocket gateways (ProtocolGateway / LocalGateway):
            Subscribes to push events, sends ``chat.send``, then waits for a
            ``DONE`` or ``ERROR`` event.

        For HTTP-only gateways (OpenAICompatGateway):
            Uses the response body from ``chat.send`` directly.

        Args:
            query: The message to send to the agent.
            options: Optional execution controls (timeout, streaming, etc.).
            callbacks: Per-call callbacks; merged with client-level callbacks.
            idempotency_key: Optional idempotency key forwarded to the gateway.

        Returns:
            An :class:`~openclaw_sdk.core.types.ExecutionResult`.

        Raises:
            AgentExecutionError: On agent-level failure or unhandled exception.
            TimeoutError: If the agent does not respond within *timeout*.
        """
        resolved_cbs = CompositeCallbackHandler(
            self._client._callbacks + list(callbacks or [])
        )
        timeout = int(
            (options.timeout_seconds if options else None)
            or self._client.config.timeout
        )

        await resolved_cbs.on_execution_start(self.agent_id, query)
        t0 = time.monotonic()

        try:
            params: dict[str, Any] = {
                "sessionKey": self.session_key,
                "message": query,
            }
            if idempotency_key is not None:
                params["idempotencyKey"] = idempotency_key

            result = await self._execute_impl(params, timeout, resolved_cbs, t0)
            await resolved_cbs.on_execution_end(self.agent_id, result)
            return result

        except OpenClawError:
            raise
        except Exception as exc:
            await resolved_cbs.on_error(self.agent_id, exc)
            raise AgentExecutionError(
                f"Agent '{self.agent_id}' execution failed: {exc}"
            ) from exc

    async def execute_stream(
        self,
        query: str,
        options: ExecutionOptions | None = None,
        callbacks: list[CallbackHandler] | None = None,
        idempotency_key: str | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """Send *query* and yield push events until the agent finishes.

        Requires a WebSocket-capable gateway.  Raises :class:`NotImplementedError`
        if the underlying gateway does not support streaming.

        Yields:
            :class:`~openclaw_sdk.core.types.StreamEvent` objects until a
            ``DONE`` or ``ERROR`` event is received.
        """
        params: dict[str, Any] = {
            "sessionKey": self.session_key,
            "message": query,
        }
        if idempotency_key is not None:
            params["idempotencyKey"] = idempotency_key

        subscriber = await self._client.gateway.subscribe()
        await self._client.gateway.call("chat.send", params)

        return self._yield_events(subscriber)

    async def _yield_events(
        self,
        subscriber: AsyncIterator[StreamEvent],
    ) -> AsyncIterator[StreamEvent]:
        async for event in subscriber:
            yield event
            if event.event_type in (EventType.DONE, EventType.ERROR):
                break

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    async def _execute_impl(
        self,
        params: dict[str, Any],
        timeout: int,
        cb: CompositeCallbackHandler,
        t0: float,
    ) -> ExecutionResult:
        """Core execution — handles both WS and HTTP-only gateways."""
        # Try to subscribe before sending so we don't miss events.
        try:
            subscriber: AsyncIterator[StreamEvent] | None = (
                await self._client.gateway.subscribe()
            )
            has_stream = True
        except NotImplementedError:
            subscriber = None
            has_stream = False

        send_result = await self._client.gateway.call("chat.send", params)

        if not has_stream or subscriber is None:
            # HTTP-only path: result comes back in the send response.
            content = (
                send_result.get("content")
                or send_result.get("text")
                or send_result.get("message")
                or ""
            )
            return ExecutionResult(
                success=True,
                content=content,
                latency_ms=int((time.monotonic() - t0) * 1000),
            )

        # WebSocket path: collect events until DONE / ERROR.
        run_id: str = send_result.get("runId", "")
        content_parts: list[str] = []

        try:
            async with asyncio.timeout(timeout):
                async for event in subscriber:
                    payload: dict[str, Any] = event.data.get("payload") or {}
                    event_run_id: str = payload.get("runId", "")

                    # Skip events that belong to a different run.
                    if run_id and event_run_id and event_run_id != run_id:
                        continue

                    if event.event_type == EventType.CONTENT:
                        chunk = payload.get("content") or payload.get("text") or ""
                        content_parts.append(chunk)
                        await cb.on_stream_event(self.agent_id, event)

                    elif event.event_type == EventType.DONE:
                        final = payload.get("content") or payload.get("text") or ""
                        if final:
                            content_parts.append(final)
                        break

                    elif event.event_type == EventType.ERROR:
                        error_msg = (
                            payload.get("message")
                            or payload.get("error")
                            or "Agent reported an error"
                        )
                        raise AgentExecutionError(
                            f"Agent '{self.agent_id}': {error_msg}"
                        )

        except asyncio.TimeoutError as exc:
            raise OcTimeoutError(
                f"Agent '{self.agent_id}' timed out after {timeout}s"
            ) from exc

        return ExecutionResult(
            success=True,
            content="".join(content_parts),
            latency_ms=int((time.monotonic() - t0) * 1000),
        )
