"""Tests for callbacks/handler.py."""
from __future__ import annotations

import pytest

from openclaw_sdk.callbacks.handler import (
    CallbackHandler,
    CompositeCallbackHandler,
    LoggingCallbackHandler,
)
from openclaw_sdk.core.constants import EventType
from openclaw_sdk.core.types import ExecutionResult, GeneratedFile, StreamEvent, TokenUsage


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_result(success: bool = True, content: str = "ok") -> ExecutionResult:
    return ExecutionResult(success=success, content=content)


def _make_file() -> GeneratedFile:
    return GeneratedFile(name="out.txt", path="/tmp/out.txt", size_bytes=10, mime_type="text/plain")


def _make_event() -> StreamEvent:
    return StreamEvent(event_type=EventType.CONTENT, data={"content": "hello"})


# ---------------------------------------------------------------------------
# CallbackHandler — default no-op implementations
# ---------------------------------------------------------------------------


class ConcreteHandler(CallbackHandler):
    """Minimal concrete subclass — uses all default no-op implementations."""


@pytest.mark.asyncio
async def test_default_noop_on_execution_start() -> None:
    h = ConcreteHandler()
    # Should not raise
    await h.on_execution_start("agent1", "hello")


@pytest.mark.asyncio
async def test_default_noop_on_llm_start() -> None:
    h = ConcreteHandler()
    await h.on_llm_start("agent1", "prompt text", "gpt-4o")


@pytest.mark.asyncio
async def test_default_noop_on_llm_end() -> None:
    h = ConcreteHandler()
    await h.on_llm_end("agent1", "response", TokenUsage(input=100, output=50), 200)


@pytest.mark.asyncio
async def test_default_noop_on_tool_call() -> None:
    h = ConcreteHandler()
    await h.on_tool_call("agent1", "search", '{"q": "python"}')


@pytest.mark.asyncio
async def test_default_noop_on_tool_result() -> None:
    h = ConcreteHandler()
    await h.on_tool_result("agent1", "search", "results here", 50)


@pytest.mark.asyncio
async def test_default_noop_on_file_generated() -> None:
    h = ConcreteHandler()
    await h.on_file_generated("agent1", _make_file())


@pytest.mark.asyncio
async def test_default_noop_on_execution_end() -> None:
    h = ConcreteHandler()
    await h.on_execution_end("agent1", _make_result())


@pytest.mark.asyncio
async def test_default_noop_on_error() -> None:
    h = ConcreteHandler()
    await h.on_error("agent1", ValueError("boom"))


@pytest.mark.asyncio
async def test_default_noop_on_stream_event() -> None:
    h = ConcreteHandler()
    await h.on_stream_event("agent1", _make_event())


# ---------------------------------------------------------------------------
# LoggingCallbackHandler — all methods callable, no errors
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_logging_handler_all_methods() -> None:
    h = LoggingCallbackHandler()
    await h.on_execution_start("agent1", "query")
    await h.on_llm_start("agent1", "prompt", "claude-sonnet-4-20250514")
    await h.on_llm_end("agent1", "resp", TokenUsage(input=10, output=20), 100)
    await h.on_tool_call("agent1", "browser", '{"url": "https://example.com"}')
    await h.on_tool_result("agent1", "browser", "<html>...</html>", 300)
    await h.on_file_generated("agent1", _make_file())
    await h.on_execution_end("agent1", _make_result())
    await h.on_error("agent1", RuntimeError("oops"))
    await h.on_stream_event("agent1", _make_event())


# ---------------------------------------------------------------------------
# CompositeCallbackHandler — fans out to all handlers
# ---------------------------------------------------------------------------


class RecordingHandler(CallbackHandler):
    """Records which events were received."""

    def __init__(self) -> None:
        self.events: list[str] = []

    async def on_execution_start(self, agent_id: str, query: str) -> None:
        self.events.append("on_execution_start")

    async def on_llm_start(self, agent_id: str, prompt: str, model: str) -> None:
        self.events.append("on_llm_start")

    async def on_llm_end(
        self,
        agent_id: str,
        response: str,
        token_usage: TokenUsage,
        duration_ms: int,
    ) -> None:
        self.events.append("on_llm_end")

    async def on_tool_call(self, agent_id: str, tool_name: str, tool_input: str) -> None:
        self.events.append("on_tool_call")

    async def on_tool_result(
        self, agent_id: str, tool_name: str, result: str, duration_ms: int
    ) -> None:
        self.events.append("on_tool_result")

    async def on_file_generated(self, agent_id: str, file: GeneratedFile) -> None:
        self.events.append("on_file_generated")

    async def on_execution_end(self, agent_id: str, result: ExecutionResult) -> None:
        self.events.append("on_execution_end")

    async def on_error(self, agent_id: str, error: Exception) -> None:
        self.events.append("on_error")

    async def on_stream_event(self, agent_id: str, event: StreamEvent) -> None:
        self.events.append("on_stream_event")


@pytest.mark.asyncio
async def test_composite_fans_out_to_all_handlers() -> None:
    h1 = RecordingHandler()
    h2 = RecordingHandler()
    composite = CompositeCallbackHandler([h1, h2])

    await composite.on_execution_start("agent1", "q")
    await composite.on_llm_start("agent1", "p", "gpt-4o")
    await composite.on_llm_end("agent1", "r", TokenUsage(), 50)
    await composite.on_tool_call("agent1", "t", "{}")
    await composite.on_tool_result("agent1", "t", "ok", 10)
    await composite.on_file_generated("agent1", _make_file())
    await composite.on_execution_end("agent1", _make_result())
    await composite.on_error("agent1", Exception("e"))
    await composite.on_stream_event("agent1", _make_event())

    expected = [
        "on_execution_start",
        "on_llm_start",
        "on_llm_end",
        "on_tool_call",
        "on_tool_result",
        "on_file_generated",
        "on_execution_end",
        "on_error",
        "on_stream_event",
    ]
    assert h1.events == expected
    assert h2.events == expected


# ---------------------------------------------------------------------------
# CompositeCallbackHandler — exception isolation
# ---------------------------------------------------------------------------


class BrokenHandler(CallbackHandler):
    """Always raises on on_error (simulates a malfunctioning handler)."""

    async def on_error(self, agent_id: str, error: Exception) -> None:
        raise RuntimeError("handler itself is broken")


@pytest.mark.asyncio
async def test_composite_broken_handler_does_not_block_others() -> None:
    broken = BrokenHandler()
    recording = RecordingHandler()
    composite = CompositeCallbackHandler([broken, recording])

    # Should NOT raise even though broken handler raises
    await composite.on_error("agent1", ValueError("original error"))

    assert "on_error" in recording.events


@pytest.mark.asyncio
async def test_composite_empty_handlers() -> None:
    composite = CompositeCallbackHandler([])
    # Should be a no-op without errors
    await composite.on_execution_start("agent1", "q")


@pytest.mark.asyncio
async def test_composite_exception_in_on_execution_start_does_not_block() -> None:
    class BrokenOnStart(CallbackHandler):
        async def on_execution_start(self, agent_id: str, query: str) -> None:
            raise RuntimeError("start failed")

    recording = RecordingHandler()
    composite = CompositeCallbackHandler([BrokenOnStart(), recording])

    await composite.on_execution_start("agent1", "q")
    assert "on_execution_start" in recording.events
