"""Tests for core/agent.py — Agent."""
from __future__ import annotations

import pytest

from openclaw_sdk.callbacks.handler import CallbackHandler
from openclaw_sdk.core.agent import Agent
from openclaw_sdk.core.client import OpenClawClient
from openclaw_sdk.core.config import ClientConfig, ExecutionOptions
from openclaw_sdk.core.constants import EventType
from openclaw_sdk.core.exceptions import AgentExecutionError
from openclaw_sdk.core.types import ExecutionResult, StreamEvent
from openclaw_sdk.gateway.mock import MockGateway


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_connected_client() -> OpenClawClient:
    mock = MockGateway()
    await mock.connect()
    return OpenClawClient(config=ClientConfig(), gateway=mock)


def _get_mock(client: OpenClawClient) -> MockGateway:
    return client.gateway  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Agent properties
# ---------------------------------------------------------------------------


def test_session_key_default() -> None:
    mock = MockGateway()
    client = OpenClawClient(config=ClientConfig(), gateway=mock)
    agent = Agent(client, "my-bot")
    assert agent.session_key == "agent:my-bot:main"


def test_session_key_custom_name() -> None:
    mock = MockGateway()
    client = OpenClawClient(config=ClientConfig(), gateway=mock)
    agent = Agent(client, "researcher", "weekly")
    assert agent.session_key == "agent:researcher:weekly"


def test_agent_id_and_session_name_accessible() -> None:
    mock = MockGateway()
    client = OpenClawClient(config=ClientConfig(), gateway=mock)
    agent = Agent(client, "bot", "s1")
    assert agent.agent_id == "bot"
    assert agent.session_name == "s1"


# ---------------------------------------------------------------------------
# execute() — happy path (DONE event carries content)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_waits_for_done_event() -> None:
    client = await _make_connected_client()
    mock = _get_mock(client)

    mock.register("chat.send", {"runId": "r1", "status": "started"})
    mock.emit_event(
        StreamEvent(
            event_type=EventType.DONE,
            data={"payload": {"runId": "r1", "content": "Hello, World!"}},
        )
    )

    agent = client.get_agent("test-bot")
    result = await agent.execute("say hello")

    assert result.success is True
    assert result.content == "Hello, World!"
    assert result.latency_ms >= 0
    await client.close()


@pytest.mark.asyncio
async def test_execute_collects_content_events() -> None:
    client = await _make_connected_client()
    mock = _get_mock(client)

    mock.register("chat.send", {"runId": "r2", "status": "started"})
    mock.emit_event(
        StreamEvent(
            event_type=EventType.CONTENT,
            data={"payload": {"runId": "r2", "content": "chunk1 "}},
        )
    )
    mock.emit_event(
        StreamEvent(
            event_type=EventType.CONTENT,
            data={"payload": {"runId": "r2", "content": "chunk2"}},
        )
    )
    mock.emit_event(
        StreamEvent(
            event_type=EventType.DONE,
            data={"payload": {"runId": "r2"}},
        )
    )

    agent = client.get_agent("streamer")
    result = await agent.execute("write something")

    assert result.content == "chunk1 chunk2"
    await client.close()


@pytest.mark.asyncio
async def test_execute_sends_correct_session_key() -> None:
    client = await _make_connected_client()
    mock = _get_mock(client)

    mock.register("chat.send", {"runId": "r3", "status": "started"})
    mock.emit_event(
        StreamEvent(event_type=EventType.DONE, data={"payload": {"content": "done"}})
    )

    agent = client.get_agent("bot", session_name="alpha")
    await agent.execute("hi")

    mock.assert_called_with("chat.send", {"sessionKey": "agent:bot:alpha", "message": "hi"})
    await client.close()


@pytest.mark.asyncio
async def test_execute_passes_idempotency_key() -> None:
    client = await _make_connected_client()
    mock = _get_mock(client)

    mock.register("chat.send", {"runId": "r4", "status": "started"})
    mock.emit_event(
        StreamEvent(event_type=EventType.DONE, data={"payload": {"content": "ok"}})
    )

    agent = client.get_agent("bot")
    await agent.execute("hello", idempotency_key="key-abc")

    mock.assert_called_with(
        "chat.send",
        {"sessionKey": "agent:bot:main", "message": "hello", "idempotencyKey": "key-abc"},
    )
    await client.close()


# ---------------------------------------------------------------------------
# execute() — HTTP-only gateway (no subscribe support)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_http_gateway_uses_direct_response() -> None:
    """An HTTP-only gateway raises NotImplementedError on subscribe.
    Agent.execute() should fall back to reading the send response directly.
    """
    from openclaw_sdk.gateway.base import Gateway
    from openclaw_sdk.core.types import HealthStatus
    from typing import Any, AsyncIterator

    class HttpOnlyMock(Gateway):
        def __init__(self) -> None:
            self._connected = False

        async def connect(self) -> None:
            self._connected = True

        async def close(self) -> None:
            self._connected = False

        async def health(self) -> HealthStatus:
            return HealthStatus(healthy=True)

        async def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
            return {"content": "HTTP response text"}

        async def subscribe(self, event_types: list[str] | None = None) -> AsyncIterator[StreamEvent]:
            raise NotImplementedError("HTTP-only")

    gw = HttpOnlyMock()
    await gw.connect()
    client = OpenClawClient(config=ClientConfig(), gateway=gw)
    agent = client.get_agent("bot")
    result = await agent.execute("query")

    assert result.success is True
    assert result.content == "HTTP response text"
    await client.close()


# ---------------------------------------------------------------------------
# execute() — ERROR event
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_raises_on_error_event() -> None:
    client = await _make_connected_client()
    mock = _get_mock(client)

    mock.register("chat.send", {"runId": "r5", "status": "started"})
    mock.emit_event(
        StreamEvent(
            event_type=EventType.ERROR,
            data={"payload": {"runId": "r5", "message": "Agent crashed"}},
        )
    )

    agent = client.get_agent("buggy-bot")
    with pytest.raises(AgentExecutionError, match="Agent crashed"):
        await agent.execute("do something")
    await client.close()


# ---------------------------------------------------------------------------
# execute() — callbacks wiring
# ---------------------------------------------------------------------------


class _RecordingCallback(CallbackHandler):
    def __init__(self) -> None:
        self.started: list[str] = []
        self.ended: list[str] = []
        self.errors: list[Exception] = []

    async def on_execution_start(self, agent_id: str, query: str) -> None:
        self.started.append(agent_id)

    async def on_execution_end(self, agent_id: str, result: ExecutionResult) -> None:
        self.ended.append(agent_id)

    async def on_error(self, agent_id: str, error: Exception) -> None:
        self.errors.append(error)


@pytest.mark.asyncio
async def test_execute_fires_callbacks() -> None:
    client = await _make_connected_client()
    mock = _get_mock(client)

    mock.register("chat.send", {"runId": "rx", "status": "started"})
    mock.emit_event(
        StreamEvent(event_type=EventType.DONE, data={"payload": {"content": "done"}})
    )

    cb = _RecordingCallback()
    agent = client.get_agent("cb-bot")
    await agent.execute("hello", callbacks=[cb])

    assert "cb-bot" in cb.started
    assert "cb-bot" in cb.ended
    await client.close()


@pytest.mark.asyncio
async def test_client_level_callbacks_fire() -> None:
    mock = MockGateway()
    await mock.connect()
    cb = _RecordingCallback()
    client = OpenClawClient(config=ClientConfig(), gateway=mock, callbacks=[cb])

    mock.register("chat.send", {"runId": "ry", "status": "started"})
    mock.emit_event(
        StreamEvent(event_type=EventType.DONE, data={"payload": {"content": "hi"}})
    )

    agent = client.get_agent("my-agent")
    await agent.execute("hi")

    assert "my-agent" in cb.started
    assert "my-agent" in cb.ended
    await client.close()


# ---------------------------------------------------------------------------
# execute() — options forwarded
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_accepts_execution_options() -> None:
    client = await _make_connected_client()
    mock = _get_mock(client)

    mock.register("chat.send", {"runId": "ro", "status": "started"})
    mock.emit_event(
        StreamEvent(event_type=EventType.DONE, data={"payload": {"content": "result"}})
    )

    options = ExecutionOptions(timeout_seconds=60)
    agent = client.get_agent("bot")
    result = await agent.execute("query", options=options)
    assert result.success is True
    await client.close()
