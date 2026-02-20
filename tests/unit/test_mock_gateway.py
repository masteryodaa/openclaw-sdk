"""Tests for MockGateway."""
from __future__ import annotations

import pytest

from openclaw_sdk.core.constants import EventType
from openclaw_sdk.core.types import StreamEvent
from openclaw_sdk.gateway.mock import MockGateway


# ------------------------------------------------------------------ #
# connect / close / health
# ------------------------------------------------------------------ #


async def test_connect_sets_connected() -> None:
    gw = MockGateway()
    assert not gw._connected
    await gw.connect()
    assert gw._connected


async def test_close_unsets_connected() -> None:
    gw = MockGateway()
    await gw.connect()
    await gw.close()
    assert not gw._connected


async def test_health_healthy_when_connected() -> None:
    gw = MockGateway()
    await gw.connect()
    status = await gw.health()
    assert status.healthy
    assert status.version == "mock"


async def test_health_unhealthy_when_disconnected() -> None:
    gw = MockGateway()
    status = await gw.health()
    assert not status.healthy


# ------------------------------------------------------------------ #
# call — static responses
# ------------------------------------------------------------------ #


async def test_call_static_response(connected_mock_gateway: MockGateway) -> None:
    connected_mock_gateway.register("sessions.list", {"sessions": [], "count": 0})
    result = await connected_mock_gateway.call("sessions.list", {})
    assert result == {"sessions": [], "count": 0}


async def test_call_dynamic_response(connected_mock_gateway: MockGateway) -> None:
    connected_mock_gateway.register(
        "chat.send",
        lambda p: {"runId": "run_1", "sessionKey": (p or {}).get("sessionKey", "")},
    )
    result = await connected_mock_gateway.call(
        "chat.send", {"sessionKey": "agent:main:main", "message": "hello"}
    )
    assert result["runId"] == "run_1"
    assert result["sessionKey"] == "agent:main:main"


async def test_call_records_history(connected_mock_gateway: MockGateway) -> None:
    connected_mock_gateway.register("cron.list", {"jobs": []})
    await connected_mock_gateway.call("cron.list", {})
    await connected_mock_gateway.call("cron.list", {})
    assert connected_mock_gateway.call_count("cron.list") == 2


async def test_call_raises_for_unregistered_method(
    connected_mock_gateway: MockGateway,
) -> None:
    with pytest.raises(KeyError, match="no response registered"):
        await connected_mock_gateway.call("unknown.method", {})


async def test_call_raises_when_not_connected(mock_gateway: MockGateway) -> None:
    mock_gateway.register("sessions.list", {"sessions": []})
    with pytest.raises(RuntimeError, match="not connected"):
        await mock_gateway.call("sessions.list")


# ------------------------------------------------------------------ #
# context manager
# ------------------------------------------------------------------ #


async def test_context_manager() -> None:
    gw = MockGateway()
    gw.register("node.list", {"nodes": []})
    async with gw:
        assert gw._connected
        result = await gw.call("node.list")
        assert result == {"nodes": []}
    assert not gw._connected


# ------------------------------------------------------------------ #
# assert helpers
# ------------------------------------------------------------------ #


async def test_assert_called(connected_mock_gateway: MockGateway) -> None:
    connected_mock_gateway.register("cron.status", {"enabled": True})
    await connected_mock_gateway.call("cron.status", {})
    connected_mock_gateway.assert_called("cron.status")


async def test_assert_called_with(connected_mock_gateway: MockGateway) -> None:
    connected_mock_gateway.register("cron.list", {"jobs": []})
    await connected_mock_gateway.call("cron.list", {})
    connected_mock_gateway.assert_called_with("cron.list", {})


async def test_assert_called_fails_if_not_called(
    connected_mock_gateway: MockGateway,
) -> None:
    with pytest.raises(AssertionError):
        connected_mock_gateway.assert_called("never.called")


# ------------------------------------------------------------------ #
# reset
# ------------------------------------------------------------------ #


async def test_reset_clears_calls_and_responses(
    connected_mock_gateway: MockGateway,
) -> None:
    connected_mock_gateway.register("sessions.list", {"sessions": []})
    await connected_mock_gateway.call("sessions.list", {})
    connected_mock_gateway.reset()
    assert connected_mock_gateway.calls == []
    with pytest.raises(KeyError):
        await connected_mock_gateway.call("sessions.list")


# ------------------------------------------------------------------ #
# emit_event / subscribe
# ------------------------------------------------------------------ #


async def test_emit_and_subscribe() -> None:
    gw = MockGateway()
    await gw.connect()

    event = StreamEvent(event_type=EventType.CONTENT, data={"text": "hello"})
    gw.emit_event(event)
    gw.close_stream()

    received = []
    async for e in await gw.subscribe():
        received.append(e)

    assert len(received) == 1
    assert received[0].event_type == EventType.CONTENT
    assert received[0].data == {"text": "hello"}


async def test_subscribe_filters_by_event_type() -> None:
    gw = MockGateway()
    await gw.connect()

    gw.emit_event(StreamEvent(event_type=EventType.THINKING, data={"t": "..."}))
    gw.emit_event(StreamEvent(event_type=EventType.CONTENT, data={"text": "hi"}))
    gw.close_stream()

    received = []
    async for e in await gw.subscribe(event_types=[EventType.CONTENT]):
        received.append(e)

    assert len(received) == 1
    assert received[0].event_type == EventType.CONTENT


# ------------------------------------------------------------------ #
# subscribe() — disconnected guard
# ------------------------------------------------------------------ #


async def test_subscribe_raises_when_disconnected() -> None:
    gw = MockGateway()
    with pytest.raises(RuntimeError, match="not connected"):
        await gw.subscribe()


# ------------------------------------------------------------------ #
# reset() — clears queue items
# ------------------------------------------------------------------ #


async def test_reset_clears_queued_events() -> None:
    gw = MockGateway()
    await gw.connect()
    gw.emit_event(StreamEvent(event_type=EventType.CONTENT, data={}))
    gw.reset()
    # After reset the queue should be empty; close_stream + subscribe yields nothing.
    gw.close_stream()
    events = [e async for e in await gw.subscribe()]
    assert events == []
