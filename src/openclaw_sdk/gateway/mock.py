from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Callable

from openclaw_sdk.core.types import HealthStatus, StreamEvent
from openclaw_sdk.gateway.base import Gateway


class MockGateway(Gateway):
    """In-memory Gateway for testing.

    Usage::

        mock = MockGateway()
        mock.register("sessions.list", {"sessions": []})          # static response
        mock.register("chat.send", lambda p: {"runId": "r1"})     # dynamic response
        await mock.connect()

        result = await mock.call("sessions.list")
        assert result == {"sessions": []}

    Push events::

        mock.emit_event(StreamEvent(event_type=EventType.CONTENT, data={"text": "hi"}))
        async for event in await mock.subscribe():
            print(event)
    """

    def __init__(self) -> None:
        self._connected = False
        self._responses: dict[str, Any] = {}
        self._event_queue: asyncio.Queue[StreamEvent | None] = asyncio.Queue()
        self.calls: list[tuple[str, dict[str, Any] | None]] = []

    # ------------------------------------------------------------------ #
    # Registration helpers
    # ------------------------------------------------------------------ #

    def register(
        self,
        method: str,
        response: dict[str, Any] | Callable[[dict[str, Any] | None], dict[str, Any]],
    ) -> None:
        """Register a static dict or a callable that receives params and returns a dict."""
        self._responses[method] = response

    def emit_event(self, event: StreamEvent) -> None:
        """Push an event into the subscription queue."""
        self._event_queue.put_nowait(event)

    def close_stream(self) -> None:
        """Signal end of event stream."""
        self._event_queue.put_nowait(None)

    # ------------------------------------------------------------------ #
    # Gateway ABC implementation
    # ------------------------------------------------------------------ #

    async def connect(self) -> None:
        self._connected = True

    async def close(self) -> None:
        self._connected = False
        self.close_stream()

    async def health(self) -> HealthStatus:
        return HealthStatus(healthy=self._connected, version="mock")

    async def call(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        if not self._connected:
            raise RuntimeError("MockGateway not connected. Call await mock.connect() first.")
        self.calls.append((method, params))
        if method not in self._responses:
            raise KeyError(f"MockGateway: no response registered for method '{method}'")
        response = self._responses[method]
        if callable(response):
            result = response(params)
        else:
            result = response
        return dict(result)

    async def subscribe(
        self, event_types: list[str] | None = None
    ) -> AsyncIterator[StreamEvent]:
        if not self._connected:
            raise RuntimeError("MockGateway not connected.")
        return self._stream_events(event_types)

    async def _stream_events(
        self, event_types: list[str] | None
    ) -> AsyncIterator[StreamEvent]:
        while True:
            event = await self._event_queue.get()
            if event is None:
                break
            if event_types is None or event.event_type in event_types:
                yield event

    # ------------------------------------------------------------------ #
    # Test helpers
    # ------------------------------------------------------------------ #

    def assert_called(self, method: str) -> None:
        methods = [c[0] for c in self.calls]
        assert method in methods, f"Expected call to '{method}', got: {methods}"

    def assert_called_with(
        self, method: str, params: dict[str, Any] | None
    ) -> None:
        assert (method, params) in self.calls, (
            f"Expected call ({method!r}, {params!r}), got: {self.calls}"
        )

    def call_count(self, method: str) -> int:
        return sum(1 for m, _ in self.calls if m == method)

    def reset(self) -> None:
        self.calls.clear()
        self._responses.clear()
        while not self._event_queue.empty():
            self._event_queue.get_nowait()
