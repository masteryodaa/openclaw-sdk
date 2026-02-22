"""Tests for tracing/otel.py -- OTelCallbackHandler."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from openclaw_sdk.core.constants import EventType
from openclaw_sdk.core.types import (
    ExecutionResult,
    GeneratedFile,
    StreamEvent,
    TokenUsage,
)
from openclaw_sdk.tracing.otel import OTelCallbackHandler


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_tracer() -> MagicMock:
    """Create a mock OTel tracer that returns mock spans."""
    tracer = MagicMock()
    span = MagicMock()
    tracer.start_span.return_value = span
    return tracer


def _make_token_usage(inp: int = 100, out: int = 50) -> TokenUsage:
    return TokenUsage(input=inp, output=out)


def _make_result(
    success: bool = True,
    content: str = "hello",
    latency_ms: int = 42,
    stop_reason: str | None = "complete",
) -> ExecutionResult:
    return ExecutionResult(
        success=success,
        content=content,
        latency_ms=latency_ms,
        token_usage=_make_token_usage(),
        stop_reason=stop_reason,
    )


# ---------------------------------------------------------------------------
# Instantiation
# ---------------------------------------------------------------------------


def test_otel_handler_can_be_instantiated() -> None:
    """OTelCallbackHandler can be created regardless of otel availability."""
    handler = OTelCallbackHandler()
    assert isinstance(handler, OTelCallbackHandler)


def test_otel_handler_with_custom_service_name() -> None:
    handler = OTelCallbackHandler(service_name="my-service")
    assert isinstance(handler, OTelCallbackHandler)


def test_otel_handler_with_explicit_tracer() -> None:
    """Providing a mock tracer sets _available=True and stores the tracer."""
    tracer = _make_mock_tracer()
    handler = OTelCallbackHandler(tracer=tracer)
    assert handler._tracer is tracer
    assert handler._available is True


# ---------------------------------------------------------------------------
# No-op when otel not installed (and no tracer provided)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_callbacks_noop_without_otel() -> None:
    """When _available is False, all callbacks should silently no-op."""
    handler = OTelCallbackHandler()
    handler._available = False
    handler._tracer = None

    # None of these should raise
    await handler.on_execution_start("agent-1", "hello")
    await handler.on_llm_start("agent-1", "prompt", "claude-sonnet-4-20250514")
    await handler.on_llm_end("agent-1", "response", _make_token_usage(), 100)
    await handler.on_tool_call("agent-1", "bash", '{"cmd": "ls"}')
    await handler.on_tool_result("agent-1", "bash", "file.txt", 50)
    await handler.on_error("agent-1", RuntimeError("boom"))
    await handler.on_execution_end("agent-1", _make_result())
    await handler.on_file_generated(
        "agent-1",
        GeneratedFile(name="f.txt", path="/tmp/f.txt", size_bytes=10, mime_type="text/plain"),
    )
    await handler.on_stream_event(
        "agent-1",
        StreamEvent(event_type=EventType.CONTENT, data={"text": "hi"}),
    )


# ---------------------------------------------------------------------------
# Span creation with mock tracer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execution_start_creates_span() -> None:
    """on_execution_start should create a root span with agent_id and query."""
    tracer = _make_mock_tracer()
    handler = OTelCallbackHandler(tracer=tracer)

    await handler.on_execution_start("agent-1", "what is 2+2?")

    tracer.start_span.assert_called_once_with(
        "agent.execute:agent-1",
        attributes={
            "openclaw.agent_id": "agent-1",
            "openclaw.query": "what is 2+2?",
        },
    )
    assert "agent-1" in handler._active_spans


@pytest.mark.asyncio
async def test_llm_end_records_token_usage() -> None:
    """on_llm_end should set token attributes on the active span."""
    tracer = _make_mock_tracer()
    span = tracer.start_span.return_value
    handler = OTelCallbackHandler(tracer=tracer)

    await handler.on_execution_start("agent-1", "query")
    await handler.on_llm_end("agent-1", "response text", _make_token_usage(200, 80), 150)

    span.set_attribute.assert_any_call("openclaw.tokens.input", 200)
    span.set_attribute.assert_any_call("openclaw.tokens.output", 80)
    span.set_attribute.assert_any_call("openclaw.llm.duration_ms", 150)
    span.set_attribute.assert_any_call("openclaw.llm.response_len", len("response text"))


@pytest.mark.asyncio
async def test_tool_call_creates_child_span() -> None:
    """on_tool_call should create a child span under the agent's root span."""
    tracer = _make_mock_tracer()
    root_span = MagicMock(name="root_span")
    child_span = MagicMock(name="child_span")
    # First call returns root, second returns child
    tracer.start_span.side_effect = [root_span, child_span]

    handler = OTelCallbackHandler(tracer=tracer)

    await handler.on_execution_start("agent-1", "query")
    await handler.on_tool_call("agent-1", "bash", '{"cmd": "ls"}')

    # Should have two start_span calls: root + child
    assert tracer.start_span.call_count == 2
    assert "agent-1:bash" in handler._tool_spans


@pytest.mark.asyncio
async def test_tool_result_ends_child_span() -> None:
    """on_tool_result should end the tool span and record result attributes."""
    tracer = _make_mock_tracer()
    root_span = MagicMock(name="root_span")
    child_span = MagicMock(name="child_span")
    tracer.start_span.side_effect = [root_span, child_span]

    handler = OTelCallbackHandler(tracer=tracer)

    await handler.on_execution_start("agent-1", "query")
    await handler.on_tool_call("agent-1", "bash", '{"cmd": "ls"}')
    await handler.on_tool_result("agent-1", "bash", "file.txt\ndir/", 75)

    child_span.set_attribute.assert_any_call("openclaw.tool.result_len", len("file.txt\ndir/"))
    child_span.set_attribute.assert_any_call("openclaw.tool.duration_ms", 75)
    child_span.end.assert_called_once()
    assert "agent-1:bash" not in handler._tool_spans


@pytest.mark.asyncio
async def test_error_records_exception_on_span() -> None:
    """on_error should record the exception and set error attributes."""
    tracer = _make_mock_tracer()
    span = tracer.start_span.return_value
    handler = OTelCallbackHandler(tracer=tracer)

    await handler.on_execution_start("agent-1", "query")
    err = RuntimeError("something went wrong")
    await handler.on_error("agent-1", err)

    span.set_attribute.assert_any_call("openclaw.error", True)
    span.set_attribute.assert_any_call("openclaw.error.message", "something went wrong")
    span.set_attribute.assert_any_call("openclaw.error.type", "RuntimeError")
    span.record_exception.assert_called_once_with(err)


@pytest.mark.asyncio
async def test_execution_end_ends_span_and_records_result() -> None:
    """on_execution_end should end the root span and set result attributes."""
    tracer = _make_mock_tracer()
    span = tracer.start_span.return_value
    handler = OTelCallbackHandler(tracer=tracer)

    await handler.on_execution_start("agent-1", "query")
    result = _make_result(success=True, content="answer", latency_ms=200)
    await handler.on_execution_end("agent-1", result)

    span.set_attribute.assert_any_call("openclaw.success", True)
    span.set_attribute.assert_any_call("openclaw.latency_ms", 200)
    span.set_attribute.assert_any_call("openclaw.content_len", len("answer"))
    span.set_attribute.assert_any_call("openclaw.stop_reason", "complete")
    span.end.assert_called_once()
    assert "agent-1" not in handler._active_spans
