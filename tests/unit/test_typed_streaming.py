"""Tests for typed streaming — execute_stream_typed() and TypedStreamEvent models."""

from __future__ import annotations

import json

from openclaw_sdk.core.agent import Agent
from openclaw_sdk.core.client import OpenClawClient
from openclaw_sdk.core.config import ClientConfig
from openclaw_sdk.core.constants import EventType
from openclaw_sdk.core.types import (
    ContentEvent,
    DoneEvent,
    ErrorEvent,
    FileEvent,
    StreamEvent,
    ThinkingEvent,
    TokenUsage,
    ToolCallEvent,
    ToolResultEvent,
    TypedStreamEvent,
)
from openclaw_sdk.gateway.mock import MockGateway


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_event(event_type: EventType, payload: dict) -> StreamEvent:
    return StreamEvent(event_type=event_type, data={"payload": payload})


async def _setup() -> tuple[OpenClawClient, Agent, MockGateway]:
    mock = MockGateway()
    await mock.connect()
    mock.register("chat.send", {"runId": "r1", "status": "started"})
    client = OpenClawClient(config=ClientConfig(), gateway=mock)
    agent = client.get_agent("test-agent")
    return client, agent, mock


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


def test_typed_stream_event_is_base() -> None:
    """TypedStreamEvent is the abstract base for all typed events."""
    event = TypedStreamEvent(event_type=EventType.CONTENT)
    assert event.event_type == EventType.CONTENT


def test_content_event_default() -> None:
    event = ContentEvent()
    assert event.event_type == EventType.CONTENT
    assert event.text == ""


def test_content_event_with_text() -> None:
    event = ContentEvent(text="hello world")
    assert event.text == "hello world"


def test_thinking_event() -> None:
    event = ThinkingEvent(thinking="reasoning step")
    assert event.event_type == EventType.THINKING
    assert event.thinking == "reasoning step"


def test_tool_call_event() -> None:
    event = ToolCallEvent(tool="bash", input='{"cmd": "ls"}')
    assert event.event_type == EventType.TOOL_CALL
    assert event.tool == "bash"
    assert event.input == '{"cmd": "ls"}'


def test_tool_result_event() -> None:
    event = ToolResultEvent(tool="bash", output="file.txt", duration_ms=42)
    assert event.event_type == EventType.TOOL_RESULT
    assert event.output == "file.txt"
    assert event.duration_ms == 42


def test_file_event() -> None:
    event = FileEvent(name="report.pdf", path="/tmp/report.pdf", size_bytes=1024)
    assert event.event_type == EventType.FILE_GENERATED
    assert event.name == "report.pdf"
    assert event.size_bytes == 1024
    assert event.mime_type == "application/octet-stream"


def test_done_event() -> None:
    usage = TokenUsage(input=100, output=50)
    event = DoneEvent(content="final answer", token_usage=usage, stop_reason="complete")
    assert event.event_type == EventType.DONE
    assert event.content == "final answer"
    assert event.token_usage.input == 100
    assert event.stop_reason == "complete"


def test_error_event() -> None:
    event = ErrorEvent(message="rate limited")
    assert event.event_type == EventType.ERROR
    assert event.message == "rate limited"


def test_isinstance_checks() -> None:
    """All typed events are TypedStreamEvent instances."""
    events = [
        ContentEvent(text="hi"),
        ThinkingEvent(thinking="hmm"),
        ToolCallEvent(tool="bash", input="ls"),
        ToolResultEvent(tool="bash", output="ok"),
        FileEvent(name="f.txt", path="/tmp/f.txt", size_bytes=0),
        DoneEvent(content="done"),
        ErrorEvent(message="err"),
    ]
    for event in events:
        assert isinstance(event, TypedStreamEvent)


# ---------------------------------------------------------------------------
# execute_stream_typed integration tests
# ---------------------------------------------------------------------------


async def test_stream_typed_content_and_done() -> None:
    """Basic content → done flow yields ContentEvent and DoneEvent."""
    _, agent, mock = await _setup()

    mock.emit_event(_make_event(EventType.CONTENT, {"content": "Hello "}))
    mock.emit_event(_make_event(EventType.CONTENT, {"content": "world!"}))
    mock.emit_event(_make_event(EventType.DONE, {
        "content": "",
        "stopReason": "complete",
        "usage": {"input": 100, "output": 50},
    }))
    mock.close_stream()

    events: list[TypedStreamEvent] = []
    async for event in agent.execute_stream_typed("Hello"):
        events.append(event)

    assert len(events) == 3
    assert isinstance(events[0], ContentEvent)
    assert events[0].text == "Hello "
    assert isinstance(events[1], ContentEvent)
    assert events[1].text == "world!"
    assert isinstance(events[2], DoneEvent)
    assert events[2].stop_reason == "complete"
    assert events[2].token_usage.input == 100


async def test_stream_typed_thinking() -> None:
    """Thinking events yield ThinkingEvent."""
    _, agent, mock = await _setup()

    mock.emit_event(_make_event(EventType.THINKING, {"thinking": "Let me think..."}))
    mock.emit_event(_make_event(EventType.CONTENT, {"content": "Answer"}))
    mock.emit_event(_make_event(EventType.DONE, {"stopReason": "complete"}))
    mock.close_stream()

    events: list[TypedStreamEvent] = []
    async for event in agent.execute_stream_typed("Think about X"):
        events.append(event)

    assert isinstance(events[0], ThinkingEvent)
    assert events[0].thinking == "Let me think..."
    assert isinstance(events[1], ContentEvent)


async def test_stream_typed_tool_call_and_result() -> None:
    """Tool call → result pairs yield ToolCallEvent and ToolResultEvent."""
    _, agent, mock = await _setup()

    mock.emit_event(_make_event(EventType.TOOL_CALL, {
        "tool": "bash",
        "input": {"cmd": "ls"},
    }))
    mock.emit_event(_make_event(EventType.TOOL_RESULT, {
        "output": "file.txt",
        "durationMs": 150,
    }))
    mock.emit_event(_make_event(EventType.DONE, {"stopReason": "complete"}))
    mock.close_stream()

    events: list[TypedStreamEvent] = []
    async for event in agent.execute_stream_typed("Run ls"):
        events.append(event)

    assert isinstance(events[0], ToolCallEvent)
    assert events[0].tool == "bash"
    assert events[0].input == json.dumps({"cmd": "ls"})
    assert isinstance(events[1], ToolResultEvent)
    assert events[1].tool == "bash"
    assert events[1].output == "file.txt"
    assert events[1].duration_ms == 150


async def test_stream_typed_file_generated() -> None:
    """File generated events yield FileEvent."""
    _, agent, mock = await _setup()

    mock.emit_event(_make_event(EventType.FILE_GENERATED, {
        "name": "report.pdf",
        "path": "/tmp/report.pdf",
        "sizeBytes": 2048,
        "mimeType": "application/pdf",
    }))
    mock.emit_event(_make_event(EventType.DONE, {"stopReason": "complete"}))
    mock.close_stream()

    events: list[TypedStreamEvent] = []
    async for event in agent.execute_stream_typed("Generate report"):
        events.append(event)

    assert isinstance(events[0], FileEvent)
    assert events[0].name == "report.pdf"
    assert events[0].size_bytes == 2048
    assert events[0].mime_type == "application/pdf"


async def test_stream_typed_error() -> None:
    """Error events yield ErrorEvent and stop iteration."""
    _, agent, mock = await _setup()

    mock.emit_event(_make_event(EventType.ERROR, {"message": "rate limited"}))
    mock.close_stream()

    events: list[TypedStreamEvent] = []
    async for event in agent.execute_stream_typed("Fail"):
        events.append(event)

    assert len(events) == 1
    assert isinstance(events[0], ErrorEvent)
    assert events[0].message == "rate limited"


async def test_stream_typed_chat_terminal_state() -> None:
    """CHAT events with terminal state yield DoneEvent."""
    _, agent, mock = await _setup()

    mock.emit_event(StreamEvent(
        event_type=EventType.CHAT,
        data={"payload": {"state": "aborted"}},
    ))
    mock.close_stream()

    events: list[TypedStreamEvent] = []
    async for event in agent.execute_stream_typed("Abort"):
        events.append(event)

    assert len(events) == 1
    assert isinstance(events[0], DoneEvent)
    assert events[0].stop_reason == "aborted"


async def test_stream_typed_pattern_matching() -> None:
    """Demonstrates pattern matching with typed events."""
    _, agent, mock = await _setup()

    mock.emit_event(_make_event(EventType.CONTENT, {"content": "The answer is 42"}))
    mock.emit_event(_make_event(EventType.DONE, {"stopReason": "complete"}))
    mock.close_stream()

    content_parts: list[str] = []
    async for event in agent.execute_stream_typed("What is 6*7?"):
        if isinstance(event, ContentEvent):
            content_parts.append(event.text)
        elif isinstance(event, DoneEvent):
            assert event.stop_reason == "complete"

    assert "".join(content_parts) == "The answer is 42"


async def test_stream_typed_done_with_token_usage() -> None:
    """DoneEvent extracts token usage from gateway payload."""
    _, agent, mock = await _setup()

    mock.emit_event(_make_event(EventType.DONE, {
        "content": "result",
        "stopReason": "complete",
        "tokenUsage": {"input": 200, "output": 100, "totalTokens": 300},
    }))
    mock.close_stream()

    events: list[TypedStreamEvent] = []
    async for event in agent.execute_stream_typed("Query"):
        events.append(event)

    assert len(events) == 1
    done = events[0]
    assert isinstance(done, DoneEvent)
    assert done.token_usage.input == 200
    assert done.token_usage.output == 100
    assert done.token_usage.total_tokens == 300
