"""Tests for the tracing module: Span, Tracer, and TracingCallbackHandler."""

from __future__ import annotations

import time

import pytest

from openclaw_sdk.core.types import ExecutionResult, TokenUsage
from openclaw_sdk.tracing.span import Span
from openclaw_sdk.tracing.tracer import Tracer, TracingCallbackHandler


# ---------------------------------------------------------------------------
# Span unit tests
# ---------------------------------------------------------------------------


class TestSpan:
    def test_span_has_id_and_name(self) -> None:
        span = Span(name="root")
        assert len(span.span_id) == 16
        assert span.name == "root"
        assert span.parent_id is None
        assert span.status == "ok"
        assert span.error is None

    def test_span_duration_none_before_end(self) -> None:
        span = Span(name="open")
        assert span.duration_ms is None

    def test_span_duration_computed_after_end(self) -> None:
        span = Span(name="timed")
        # Simulate a small delay so duration > 0
        time.sleep(0.01)
        span.end()
        assert span.duration_ms is not None
        assert span.duration_ms >= 0

    def test_span_end_idempotent(self) -> None:
        span = Span(name="idem")
        span.end()
        first_end = span.end_time
        span.end()
        assert span.end_time == first_end

    def test_span_attributes(self) -> None:
        span = Span(name="attrs")
        span.set_attribute("key1", "value1")
        span.set_attribute("key2", 42)
        assert span.attributes == {"key1": "value1", "key2": 42}

    def test_span_error(self) -> None:
        span = Span(name="err")
        span.set_error("something broke")
        assert span.status == "error"
        assert span.error == "something broke"

    def test_span_to_dict(self) -> None:
        span = Span(name="dict_test", agent_id="a1", parent_id="p1")
        span.set_attribute("foo", "bar")
        span.end()
        d = span.to_dict()
        assert d["span_id"] == span.span_id
        assert d["parent_id"] == "p1"
        assert d["name"] == "dict_test"
        assert d["agent_id"] == "a1"
        assert d["status"] == "ok"
        assert d["error"] is None
        assert d["duration_ms"] is not None
        assert d["attributes"] == {"foo": "bar"}


# ---------------------------------------------------------------------------
# Tracer unit tests
# ---------------------------------------------------------------------------


class TestTracer:
    def test_tracer_creates_root_span(self) -> None:
        tracer = Tracer()
        span = tracer.start_span("root", agent_id="agent-1")
        assert span.parent_id is None
        assert span.agent_id == "agent-1"
        assert span.name == "root"
        assert tracer.get_traces() == [span]

    def test_tracer_creates_child_span(self) -> None:
        tracer = Tracer()
        root = tracer.start_span("root")
        child = tracer.start_span("child", parent=root)
        assert child.parent_id == root.span_id
        assert len(tracer.get_traces()) == 2

    def test_tracer_end_span(self) -> None:
        tracer = Tracer()
        span = tracer.start_span("s")
        assert span.end_time is None
        tracer.end_span(span)
        assert span.end_time is not None

    def test_tracer_export_json(self) -> None:
        tracer = Tracer()
        root = tracer.start_span("root", agent_id="a")
        child = tracer.start_span("child", parent=root, tool="bash")
        tracer.end_span(child)
        tracer.end_span(root)
        exported = tracer.export_json()
        assert isinstance(exported, list)
        assert len(exported) == 2
        # Verify they are plain dicts
        assert all(isinstance(e, dict) for e in exported)
        assert exported[0]["name"] == "root"
        assert exported[1]["name"] == "child"
        assert exported[1]["parent_id"] == root.span_id

    def test_tracer_start_span_with_attributes(self) -> None:
        tracer = Tracer()
        span = tracer.start_span("with_attrs", query="hello", model="gpt-4")
        assert span.attributes == {"query": "hello", "model": "gpt-4"}

    def test_tracer_clear(self) -> None:
        tracer = Tracer()
        tracer.start_span("a")
        tracer.start_span("b")
        assert len(tracer.get_traces()) == 2
        tracer.clear()
        assert len(tracer.get_traces()) == 0

    def test_tracer_get_traces_returns_copy(self) -> None:
        tracer = Tracer()
        tracer.start_span("x")
        traces = tracer.get_traces()
        traces.clear()
        # Original list should be unaffected
        assert len(tracer.get_traces()) == 1


# ---------------------------------------------------------------------------
# TracingCallbackHandler tests
# ---------------------------------------------------------------------------


class TestTracingCallbackHandler:
    @pytest.fixture()
    def setup(self) -> tuple[Tracer, TracingCallbackHandler]:
        tracer = Tracer()
        handler = TracingCallbackHandler(tracer)
        return tracer, handler

    async def test_tracing_callback_execution(
        self, setup: tuple[Tracer, TracingCallbackHandler]
    ) -> None:
        tracer, handler = setup
        await handler.on_execution_start("agent-1", "hello")

        spans = tracer.get_traces()
        assert len(spans) == 1
        root = spans[0]
        assert root.name == "agent_run"
        assert root.agent_id == "agent-1"
        assert root.parent_id is None
        assert root.attributes["query"] == "hello"
        assert root.end_time is None  # still open

        result = ExecutionResult(
            success=True,
            content="done",
            latency_ms=123,
            token_usage=TokenUsage(input=10, output=20),
        )
        await handler.on_execution_end("agent-1", result)

        assert root.end_time is not None
        assert root.attributes["success"] is True
        assert root.attributes["latency_ms"] == 123
        assert root.attributes["input_tokens"] == 10
        assert root.attributes["output_tokens"] == 20

    async def test_tracing_callback_tool(
        self, setup: tuple[Tracer, TracingCallbackHandler]
    ) -> None:
        tracer, handler = setup

        # Start an execution first to create a root span
        await handler.on_execution_start("agent-1", "run tools")
        root = tracer.get_traces()[0]

        # Tool call
        await handler.on_tool_call("agent-1", "bash", '{"cmd": "ls"}')
        spans = tracer.get_traces()
        assert len(spans) == 2
        tool_span = spans[1]
        assert tool_span.name == "tool:bash"
        assert tool_span.parent_id == root.span_id
        assert tool_span.agent_id == "agent-1"
        assert tool_span.attributes["tool_input"] == '{"cmd": "ls"}'

        # Tool result
        await handler.on_tool_result("agent-1", "bash", "file1\nfile2", 50)
        assert tool_span.end_time is not None
        assert tool_span.attributes["result_len"] == len("file1\nfile2")
        assert tool_span.attributes["duration_ms"] == 50

    async def test_tracing_callback_error(
        self, setup: tuple[Tracer, TracingCallbackHandler]
    ) -> None:
        tracer, handler = setup

        await handler.on_execution_start("agent-1", "will fail")
        root = tracer.get_traces()[0]

        await handler.on_error("agent-1", RuntimeError("boom"))
        assert root.status == "error"
        assert root.error == "boom"
        assert root.end_time is not None

    async def test_tracing_callback_tool_without_root(
        self, setup: tuple[Tracer, TracingCallbackHandler]
    ) -> None:
        """Tool call without a prior execution_start still works (no parent)."""
        tracer, handler = setup
        await handler.on_tool_call("agent-1", "bash", "echo hi")
        spans = tracer.get_traces()
        assert len(spans) == 1
        assert spans[0].parent_id is None

    async def test_tracing_callback_tool_result_without_call(
        self, setup: tuple[Tracer, TracingCallbackHandler]
    ) -> None:
        """tool_result for a tool that was never started is a no-op."""
        tracer, handler = setup
        await handler.on_tool_result("agent-1", "bash", "output", 10)
        # No spans should have been created or ended
        assert len(tracer.get_traces()) == 0

    async def test_tracing_callback_execution_end_without_start(
        self, setup: tuple[Tracer, TracingCallbackHandler]
    ) -> None:
        """execution_end without a prior start is a no-op."""
        tracer, handler = setup
        result = ExecutionResult(success=True, content="ok")
        await handler.on_execution_end("agent-1", result)
        assert len(tracer.get_traces()) == 0

    async def test_tracing_callback_error_without_start(
        self, setup: tuple[Tracer, TracingCallbackHandler]
    ) -> None:
        """on_error without a prior start is a no-op."""
        tracer, handler = setup
        await handler.on_error("agent-1", RuntimeError("oops"))
        assert len(tracer.get_traces()) == 0
