"""Tests for Agent.stream_events() -- typed event filtering."""

from __future__ import annotations

import pytest

from openclaw_sdk.core.client import OpenClawClient
from openclaw_sdk.core.config import ClientConfig
from openclaw_sdk.core.constants import EventType
from openclaw_sdk.core.types import StreamEvent
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
# stream_events() — basic yield
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stream_events_yields_all_events() -> None:
    """With no event_types filter, all events should be yielded."""
    client = await _make_connected_client()
    mock = _get_mock(client)

    mock.register("chat.send", {"runId": "r1", "status": "started"})
    mock.emit_event(
        StreamEvent(
            event_type=EventType.CONTENT,
            data={"payload": {"content": "chunk1"}},
        )
    )
    mock.emit_event(
        StreamEvent(
            event_type=EventType.TOOL_CALL,
            data={"payload": {"tool": "bash", "input": "ls"}},
        )
    )
    mock.emit_event(
        StreamEvent(
            event_type=EventType.DONE,
            data={"payload": {"content": "final"}},
        )
    )

    agent = client.get_agent("bot")
    events: list[StreamEvent] = []
    async for event in agent.stream_events("hello"):
        events.append(event)

    assert len(events) == 3
    assert events[0].event_type == EventType.CONTENT
    assert events[1].event_type == EventType.TOOL_CALL
    assert events[2].event_type == EventType.DONE
    await client.close()


# ---------------------------------------------------------------------------
# stream_events() — event_types filtering
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stream_events_filters_by_event_type() -> None:
    """Only events matching the filter should be yielded."""
    client = await _make_connected_client()
    mock = _get_mock(client)

    mock.register("chat.send", {"runId": "r2", "status": "started"})
    mock.emit_event(
        StreamEvent(
            event_type=EventType.CONTENT,
            data={"payload": {"content": "text"}},
        )
    )
    mock.emit_event(
        StreamEvent(
            event_type=EventType.THINKING,
            data={"payload": {"thinking": "reasoning..."}},
        )
    )
    mock.emit_event(
        StreamEvent(
            event_type=EventType.TOOL_CALL,
            data={"payload": {"tool": "bash", "input": "pwd"}},
        )
    )
    mock.emit_event(
        StreamEvent(
            event_type=EventType.DONE,
            data={"payload": {"content": "done"}},
        )
    )

    agent = client.get_agent("filter-bot")
    events: list[StreamEvent] = []
    async for event in agent.stream_events("query", event_types=["content", "tool_call"]):
        events.append(event)

    # Should only get CONTENT and TOOL_CALL -- not THINKING, not DONE
    assert len(events) == 2
    assert events[0].event_type == EventType.CONTENT
    assert events[1].event_type == EventType.TOOL_CALL
    await client.close()


# ---------------------------------------------------------------------------
# stream_events() — stops on ERROR
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stream_events_stops_on_error() -> None:
    """The stream should stop on ERROR events."""
    client = await _make_connected_client()
    mock = _get_mock(client)

    mock.register("chat.send", {"runId": "r3", "status": "started"})
    mock.emit_event(
        StreamEvent(
            event_type=EventType.CONTENT,
            data={"payload": {"content": "partial"}},
        )
    )
    mock.emit_event(
        StreamEvent(
            event_type=EventType.ERROR,
            data={"payload": {"error": "crashed"}},
        )
    )
    # This should never be reached
    mock.emit_event(
        StreamEvent(
            event_type=EventType.CONTENT,
            data={"payload": {"content": "never"}},
        )
    )

    agent = client.get_agent("error-bot")
    events: list[StreamEvent] = []
    async for event in agent.stream_events("query"):
        events.append(event)

    assert len(events) == 2
    assert events[-1].event_type == EventType.ERROR
    await client.close()


# ---------------------------------------------------------------------------
# stream_events() — stops on chat final state
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stream_events_stops_on_chat_final() -> None:
    """Chat events with state=final should terminate the stream."""
    client = await _make_connected_client()
    mock = _get_mock(client)

    mock.register("chat.send", {"runId": "r4", "status": "started"})
    mock.emit_event(
        StreamEvent(
            event_type=EventType.CHAT,
            data={
                "payload": {
                    "state": "final",
                    "message": {"content": "done"},
                }
            },
        )
    )

    agent = client.get_agent("chat-bot")
    events: list[StreamEvent] = []
    async for event in agent.stream_events("query"):
        events.append(event)

    assert len(events) == 1
    assert events[0].event_type == EventType.CHAT
    await client.close()


# ---------------------------------------------------------------------------
# stream_events() — filtered terminal event still terminates
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stream_events_terminal_filtered_out_still_stops() -> None:
    """Even if DONE is filtered out, the stream should still stop."""
    client = await _make_connected_client()
    mock = _get_mock(client)

    mock.register("chat.send", {"runId": "r5", "status": "started"})
    mock.emit_event(
        StreamEvent(
            event_type=EventType.CONTENT,
            data={"payload": {"content": "text"}},
        )
    )
    mock.emit_event(
        StreamEvent(
            event_type=EventType.DONE,
            data={"payload": {"content": "final"}},
        )
    )

    agent = client.get_agent("terminal-bot")
    events: list[StreamEvent] = []
    # Only ask for CONTENT events, not DONE
    async for event in agent.stream_events("query", event_types=["content"]):
        events.append(event)

    # Only CONTENT should be yielded, but the stream should terminate
    assert len(events) == 1
    assert events[0].event_type == EventType.CONTENT
    await client.close()
