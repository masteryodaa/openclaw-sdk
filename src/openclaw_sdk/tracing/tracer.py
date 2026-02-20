"""Tracer and TracingCallbackHandler -- hierarchical execution tracing."""

from __future__ import annotations

from typing import Any

from openclaw_sdk.callbacks.handler import CallbackHandler
from openclaw_sdk.core.types import ExecutionResult
from openclaw_sdk.tracing.span import Span


class Tracer:
    """Collects :class:`Span` objects into a flat list for later export.

    Usage::

        tracer = Tracer()
        root = tracer.start_span("agent_run", agent_id="main")
        child = tracer.start_span("tool_call", parent=root, tool="bash")
        tracer.end_span(child)
        tracer.end_span(root)
        print(tracer.export_json())
    """

    def __init__(self) -> None:
        self._spans: list[Span] = []

    def start_span(
        self,
        name: str,
        agent_id: str | None = None,
        parent: Span | None = None,
        **attributes: Any,
    ) -> Span:
        """Create and register a new span.

        Parameters
        ----------
        name:
            Human-readable label (e.g. ``"agent_run"``, ``"tool:bash"``).
        agent_id:
            The agent this span belongs to, if applicable.
        parent:
            Optional parent span -- the new span's ``parent_id`` will be set to
            the parent's ``span_id``.
        **attributes:
            Arbitrary key/value pairs attached to the span.
        """
        parent_id = parent.span_id if parent is not None else None
        span = Span(name=name, agent_id=agent_id, parent_id=parent_id)
        for key, value in attributes.items():
            span.set_attribute(key, value)
        self._spans.append(span)
        return span

    def end_span(self, span: Span) -> None:
        """End a span (records its ``end_time``)."""
        span.end()

    def get_traces(self) -> list[Span]:
        """Return all collected spans (including still-open ones)."""
        return list(self._spans)

    def export_json(self) -> list[dict[str, Any]]:
        """Serialise all spans to a list of plain dictionaries."""
        return [s.to_dict() for s in self._spans]

    def clear(self) -> None:
        """Discard all collected spans."""
        self._spans.clear()


class TracingCallbackHandler(CallbackHandler):
    """A :class:`CallbackHandler` that automatically creates spans.

    Integrates with an existing :class:`Tracer` so every execution and tool
    call is recorded as a hierarchical span tree.
    """

    def __init__(self, tracer: Tracer) -> None:
        self._tracer = tracer
        self._active_spans: dict[str, Span] = {}

    async def on_execution_start(self, agent_id: str, query: str) -> None:
        """Create a root span for the agent execution."""
        span = self._tracer.start_span(
            "agent_run", agent_id=agent_id, query=query
        )
        self._active_spans[agent_id] = span

    async def on_tool_call(
        self, agent_id: str, tool_name: str, tool_input: str
    ) -> None:
        """Create a child span under the agent's root span."""
        parent = self._active_spans.get(agent_id)
        span = self._tracer.start_span(
            f"tool:{tool_name}",
            agent_id=agent_id,
            parent=parent,
            tool_input=tool_input,
        )
        self._active_spans[f"{agent_id}:tool:{tool_name}"] = span

    async def on_tool_result(
        self, agent_id: str, tool_name: str, result: str, duration_ms: int
    ) -> None:
        """End the tool span and record the result length."""
        key = f"{agent_id}:tool:{tool_name}"
        span = self._active_spans.pop(key, None)
        if span is not None:
            span.set_attribute("result_len", len(result))
            span.set_attribute("duration_ms", duration_ms)
            self._tracer.end_span(span)

    async def on_execution_end(
        self, agent_id: str, result: ExecutionResult
    ) -> None:
        """End the root span, recording success / latency / token counts."""
        span = self._active_spans.pop(agent_id, None)
        if span is not None:
            span.set_attribute("success", result.success)
            span.set_attribute("latency_ms", result.latency_ms)
            span.set_attribute("input_tokens", result.token_usage.input)
            span.set_attribute("output_tokens", result.token_usage.output)
            self._tracer.end_span(span)

    async def on_error(self, agent_id: str, error: Exception) -> None:
        """Mark the root span as errored and end it."""
        span = self._active_spans.pop(agent_id, None)
        if span is not None:
            span.set_error(str(error))
            self._tracer.end_span(span)
