"""Edge case tests for core/agent.py."""
from __future__ import annotations

import asyncio
import unittest.mock as mock_lib

import pytest

from openclaw_sdk.core.agent import Agent
from openclaw_sdk.core.client import OpenClawClient
from openclaw_sdk.core.config import ClientConfig, ExecutionOptions
from openclaw_sdk.core.constants import EventType
from openclaw_sdk.core.exceptions import AgentExecutionError, OpenClawError
from openclaw_sdk.core.exceptions import TimeoutError as OcTimeoutError
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
# runId filtering — events with different runId are skipped
# ---------------------------------------------------------------------------


async def test_execute_skips_events_with_different_run_id() -> None:
    """Events whose runId does not match the current run's runId must be skipped."""
    client = await _make_connected_client()
    mock = _get_mock(client)

    # Gateway returns runId "run-A"
    mock.register("chat.send", {"runId": "run-A"})

    # First emit an event for a *different* run, then the correct DONE event
    mock.emit_event(
        StreamEvent(
            event_type=EventType.CONTENT,
            data={"payload": {"runId": "run-B", "content": "wrong run content"}},
        )
    )
    mock.emit_event(
        StreamEvent(
            event_type=EventType.DONE,
            data={"payload": {"runId": "run-A", "content": "correct content"}},
        )
    )

    agent = client.get_agent("filter-bot")
    result = await agent.execute("query")

    # The content from the wrong run should NOT be included
    assert "wrong run content" not in result.content
    assert result.content == "correct content"
    await client.close()


async def test_execute_includes_events_with_empty_run_id() -> None:
    """Events without a runId should NOT be filtered (pass through)."""
    client = await _make_connected_client()
    mock = _get_mock(client)

    mock.register("chat.send", {"runId": "run-X"})

    # Event without runId in payload — should be included
    mock.emit_event(
        StreamEvent(
            event_type=EventType.CONTENT,
            data={"payload": {"content": "no-run-id chunk"}},
        )
    )
    mock.emit_event(
        StreamEvent(
            event_type=EventType.DONE,
            data={"payload": {}},
        )
    )

    agent = client.get_agent("norun-bot")
    result = await agent.execute("query")

    assert "no-run-id chunk" in result.content
    await client.close()


async def test_execute_no_run_id_from_send_accepts_all_events() -> None:
    """When chat.send returns no runId, all events should be accepted."""
    client = await _make_connected_client()
    mock = _get_mock(client)

    # Gateway returns no runId
    mock.register("chat.send", {})

    mock.emit_event(
        StreamEvent(
            event_type=EventType.CONTENT,
            data={"payload": {"runId": "some-run", "content": "chunk"}},
        )
    )
    mock.emit_event(
        StreamEvent(
            event_type=EventType.DONE,
            data={"payload": {}},
        )
    )

    agent = client.get_agent("norunid-bot")
    result = await agent.execute("query")

    assert "chunk" in result.content
    await client.close()


# ---------------------------------------------------------------------------
# Timeout path
# ---------------------------------------------------------------------------


async def test_execute_raises_timeout_error() -> None:
    """Agent.execute should raise OcTimeoutError when the gateway never responds."""
    client = await _make_connected_client()
    mock = _get_mock(client)

    mock.register("chat.send", {"runId": "rt1"})
    # Emit nothing — stream will block indefinitely

    agent = client.get_agent("slow-bot")
    options = ExecutionOptions(timeout_seconds=1)

    with pytest.raises(OcTimeoutError, match="timed out"):
        await agent.execute("hang forever", options=options)

    await client.close()


# ---------------------------------------------------------------------------
# Non-OpenClawError exception → wrapped as AgentExecutionError
# ---------------------------------------------------------------------------


async def test_execute_wraps_non_openclaw_errors() -> None:
    """If the gateway raises a plain Exception, it should be wrapped as AgentExecutionError."""
    from openclaw_sdk.gateway.base import Gateway
    from openclaw_sdk.core.types import HealthStatus
    from typing import Any, AsyncIterator

    class BrokenGateway(Gateway):
        async def connect(self) -> None:
            pass

        async def close(self) -> None:
            pass

        async def health(self) -> HealthStatus:
            return HealthStatus(healthy=True)

        async def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
            raise ValueError("unexpected internal error")

        async def subscribe(
            self, event_types: list[str] | None = None
        ) -> AsyncIterator[StreamEvent]:
            raise NotImplementedError

    gw = BrokenGateway()
    await gw.connect()
    client = OpenClawClient(config=ClientConfig(), gateway=gw)
    agent = client.get_agent("broken-bot")

    with pytest.raises(AgentExecutionError, match="execution failed"):
        await agent.execute("query")

    await client.close()


# ---------------------------------------------------------------------------
# OpenClawError is re-raised as-is (not wrapped)
# ---------------------------------------------------------------------------


async def test_execute_reraises_openclaw_errors_unchanged() -> None:
    """OpenClawError subclasses should propagate without wrapping."""
    from openclaw_sdk.gateway.base import Gateway
    from openclaw_sdk.core.types import HealthStatus
    from typing import Any, AsyncIterator

    class OpenClawErrorGateway(Gateway):
        async def connect(self) -> None:
            pass

        async def close(self) -> None:
            pass

        async def health(self) -> HealthStatus:
            return HealthStatus(healthy=True)

        async def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
            from openclaw_sdk.core.exceptions import GatewayError
            raise GatewayError("gateway exploded", code="GW_ERR")

        async def subscribe(
            self, event_types: list[str] | None = None
        ) -> AsyncIterator[StreamEvent]:
            raise NotImplementedError

    gw = OpenClawErrorGateway()
    await gw.connect()
    client = OpenClawClient(config=ClientConfig(), gateway=gw)
    agent = client.get_agent("openclaw-err-bot")

    from openclaw_sdk.core.exceptions import GatewayError

    with pytest.raises(GatewayError, match="gateway exploded"):
        await agent.execute("query")

    await client.close()


# ---------------------------------------------------------------------------
# ERROR event with alternative payload keys
# ---------------------------------------------------------------------------


async def test_execute_error_event_with_error_key() -> None:
    """ERROR event using 'error' key instead of 'message' should still raise."""
    client = await _make_connected_client()
    mock = _get_mock(client)

    mock.register("chat.send", {"runId": "re1"})
    mock.emit_event(
        StreamEvent(
            event_type=EventType.ERROR,
            data={"payload": {"runId": "re1", "error": "Something exploded"}},
        )
    )

    agent = client.get_agent("err-bot")
    with pytest.raises(AgentExecutionError, match="Something exploded"):
        await agent.execute("query")

    await client.close()


async def test_execute_error_event_empty_payload_uses_default_message() -> None:
    """ERROR event with empty payload should use a default error message."""
    client = await _make_connected_client()
    mock = _get_mock(client)

    mock.register("chat.send", {"runId": "re2"})
    mock.emit_event(
        StreamEvent(
            event_type=EventType.ERROR,
            data={"payload": {}},
        )
    )

    agent = client.get_agent("err-bot2")
    with pytest.raises(AgentExecutionError, match="Agent reported an error"):
        await agent.execute("query")

    await client.close()


# ---------------------------------------------------------------------------
# HTTP-only gateway — text / message fallback
# ---------------------------------------------------------------------------


async def test_execute_http_gateway_text_field_fallback() -> None:
    """For HTTP-only gateways, 'text' field should be used if 'content' is absent."""
    from openclaw_sdk.gateway.base import Gateway
    from openclaw_sdk.core.types import HealthStatus
    from typing import Any, AsyncIterator

    class TextFieldGateway(Gateway):
        async def connect(self) -> None:
            pass

        async def close(self) -> None:
            pass

        async def health(self) -> HealthStatus:
            return HealthStatus(healthy=True)

        async def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
            return {"text": "text field response"}

        async def subscribe(
            self, event_types: list[str] | None = None
        ) -> AsyncIterator[StreamEvent]:
            raise NotImplementedError

    gw = TextFieldGateway()
    await gw.connect()
    client = OpenClawClient(config=ClientConfig(), gateway=gw)
    agent = client.get_agent("text-bot")
    result = await agent.execute("query")

    assert result.content == "text field response"
    await client.close()


async def test_execute_http_gateway_message_field_fallback() -> None:
    """For HTTP-only gateways, 'message' field should be used if 'content' and 'text' absent."""
    from openclaw_sdk.gateway.base import Gateway
    from openclaw_sdk.core.types import HealthStatus
    from typing import Any, AsyncIterator

    class MessageFieldGateway(Gateway):
        async def connect(self) -> None:
            pass

        async def close(self) -> None:
            pass

        async def health(self) -> HealthStatus:
            return HealthStatus(healthy=True)

        async def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
            return {"message": "message field response"}

        async def subscribe(
            self, event_types: list[str] | None = None
        ) -> AsyncIterator[StreamEvent]:
            raise NotImplementedError

    gw = MessageFieldGateway()
    await gw.connect()
    client = OpenClawClient(config=ClientConfig(), gateway=gw)
    agent = client.get_agent("msg-bot")
    result = await agent.execute("query")

    assert result.content == "message field response"
    await client.close()


# ---------------------------------------------------------------------------
# _build_gateway — local mode
# ---------------------------------------------------------------------------


def test_build_gateway_local_mode_creates_local_gateway() -> None:
    from openclaw_sdk.gateway.local import LocalGateway

    config = ClientConfig(mode="local")
    gw = OpenClawClient._build_gateway(config)
    assert isinstance(gw, LocalGateway)


def test_build_gateway_auto_mode_with_running_openclaw_creates_local_gateway() -> None:
    from openclaw_sdk.gateway.local import LocalGateway

    config = ClientConfig(mode="auto")
    with mock_lib.patch(
        "openclaw_sdk.core.client._openclaw_is_running", return_value=True
    ):
        gw = OpenClawClient._build_gateway(config)
    assert isinstance(gw, LocalGateway)


# ---------------------------------------------------------------------------
# execute_stream — delegating method
# ---------------------------------------------------------------------------


async def test_execute_stream_delegates_to_gateway_subscribe() -> None:
    """execute_stream() should call subscribe() and chat.send, then yield events."""
    client = await _make_connected_client()
    mock = _get_mock(client)

    mock.register("chat.send", {"runId": "rs1"})
    mock.emit_event(
        StreamEvent(event_type=EventType.CONTENT, data={"payload": {"content": "hello"}})
    )
    mock.emit_event(
        StreamEvent(event_type=EventType.DONE, data={"payload": {}})
    )

    agent = client.get_agent("stream-bot")
    stream = await agent.execute_stream("query")
    events = []
    async for event in stream:
        events.append(event)
        if event.event_type in (EventType.DONE, EventType.ERROR):
            break

    assert any(e.event_type == EventType.DONE for e in events)
    await client.close()
