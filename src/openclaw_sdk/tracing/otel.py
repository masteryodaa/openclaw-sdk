"""OpenTelemetry callback handler -- optional OTel integration.

Requires the ``opentelemetry-api`` package::

    pip install opentelemetry-api

If the package is not installed, the handler logs a warning on instantiation
and all callback methods become silent no-ops.

Usage::

    from openclaw_sdk.tracing.otel import OTelCallbackHandler

    handler = OTelCallbackHandler(service_name="my-app")
    client = await OpenClawClient.connect(callbacks=[handler])
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

import structlog

from openclaw_sdk.callbacks.handler import CallbackHandler
from openclaw_sdk.core.types import ExecutionResult, GeneratedFile, StreamEvent, TokenUsage

if TYPE_CHECKING:
    from opentelemetry.trace import Span as OTelSpan, Tracer as OTelTracer

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Detect whether opentelemetry is available at runtime.
# ---------------------------------------------------------------------------

_HAS_OTEL = False
try:
    from opentelemetry import trace as _otel_trace  # noqa: F401

    _HAS_OTEL = True
except ImportError:  # pragma: no cover
    pass


def _get_tracer(service_name: str) -> OTelTracer | None:
    """Return an OTel tracer if the SDK is installed, else ``None``."""
    if not _HAS_OTEL:
        return None
    from opentelemetry import trace  # noqa: PLC0415

    return trace.get_tracer(service_name)


class OTelCallbackHandler(CallbackHandler):
    """A :class:`CallbackHandler` that creates OpenTelemetry spans.

    Each agent execution becomes a root span. Tool calls become child spans.
    Token usage, errors, and latency are recorded as span attributes.

    If ``opentelemetry-api`` is not installed and no explicit *tracer* is
    provided, the handler emits a single warning and all methods silently
    no-op.

    When an explicit *tracer* is provided (e.g. a mock for testing), the
    handler assumes the tracer implements the OTel ``Tracer`` interface
    and uses it directly without importing ``opentelemetry``.

    Args:
        service_name: The OTel service name used to obtain a tracer.
            Defaults to ``"openclaw-sdk"``.
        tracer: An explicit :class:`opentelemetry.trace.Tracer` instance.
            If provided, *service_name* is ignored.
    """

    def __init__(
        self,
        service_name: str = "openclaw-sdk",
        tracer: OTelTracer | None = None,
    ) -> None:
        self._active_spans: dict[str, OTelSpan] = {}
        self._tool_spans: dict[str, OTelSpan] = {}
        self._exec_start_times: dict[str, float] = {}

        if tracer is not None:
            # Explicit tracer provided -- assume OTel-compatible API.
            self._available = True
            self._tracer: OTelTracer | None = tracer
        elif _HAS_OTEL:
            self._available = True
            self._tracer = _get_tracer(service_name)
        else:
            self._available = False
            self._tracer = None
            logger.warning(
                "opentelemetry_not_installed",
                hint="pip install opentelemetry-api to enable OTel tracing",
            )

    # ------------------------------------------------------------------ #
    # Callback methods
    # ------------------------------------------------------------------ #

    async def on_execution_start(self, agent_id: str, query: str) -> None:
        """Start a root span for the agent execution."""
        if not self._available or self._tracer is None:
            return

        span = self._tracer.start_span(
            f"agent.execute:{agent_id}",
            attributes={
                "openclaw.agent_id": agent_id,
                "openclaw.query": query,
            },
        )
        self._active_spans[agent_id] = span
        self._exec_start_times[agent_id] = time.monotonic()

    async def on_llm_start(self, agent_id: str, prompt: str, model: str) -> None:
        """Record LLM model on the active span."""
        if not self._available:
            return
        span = self._active_spans.get(agent_id)
        if span is not None:
            span.set_attribute("openclaw.llm.model", model)
            span.set_attribute("openclaw.llm.prompt_len", len(prompt))

    async def on_llm_end(
        self,
        agent_id: str,
        response: str,
        token_usage: TokenUsage,
        duration_ms: int,
    ) -> None:
        """Record token usage on the active span."""
        if not self._available:
            return
        span = self._active_spans.get(agent_id)
        if span is not None:
            span.set_attribute("openclaw.tokens.input", token_usage.input)
            span.set_attribute("openclaw.tokens.output", token_usage.output)
            span.set_attribute("openclaw.tokens.total", token_usage.total)
            span.set_attribute("openclaw.llm.duration_ms", duration_ms)
            span.set_attribute("openclaw.llm.response_len", len(response))

    async def on_tool_call(
        self, agent_id: str, tool_name: str, tool_input: str
    ) -> None:
        """Create a child span for the tool call."""
        if not self._available or self._tracer is None:
            return

        parent_span = self._active_spans.get(agent_id)
        if parent_span is not None:
            # When the real opentelemetry SDK is available, create a proper
            # parent context so the child span is linked.  When using a mock
            # tracer (otel not installed), just start a plain child span.
            kwargs: dict[str, Any] = {
                "attributes": {
                    "openclaw.tool.name": tool_name,
                    "openclaw.tool.input_len": len(tool_input),
                },
            }
            if _HAS_OTEL:
                from opentelemetry import trace  # noqa: PLC0415

                kwargs["context"] = trace.set_span_in_context(parent_span)

            child_span = self._tracer.start_span(f"tool:{tool_name}", **kwargs)
            self._tool_spans[f"{agent_id}:{tool_name}"] = child_span

    async def on_tool_result(
        self, agent_id: str, tool_name: str, result: str, duration_ms: int
    ) -> None:
        """End the tool child span and record results."""
        if not self._available:
            return
        key = f"{agent_id}:{tool_name}"
        span = self._tool_spans.pop(key, None)
        if span is not None:
            span.set_attribute("openclaw.tool.result_len", len(result))
            span.set_attribute("openclaw.tool.duration_ms", duration_ms)
            span.end()

    async def on_error(self, agent_id: str, error: Exception) -> None:
        """Record the exception on the active span."""
        if not self._available:
            return
        span = self._active_spans.get(agent_id)
        if span is not None:
            span.set_attribute("openclaw.error", True)
            span.set_attribute("openclaw.error.message", str(error))
            span.set_attribute("openclaw.error.type", type(error).__name__)
            span.record_exception(error)
            if _HAS_OTEL:
                from opentelemetry.trace import StatusCode  # noqa: PLC0415

                span.set_status(StatusCode.ERROR, str(error))

    async def on_execution_end(self, agent_id: str, result: ExecutionResult) -> None:
        """End the root span and record latency and success."""
        if not self._available:
            return
        span = self._active_spans.pop(agent_id, None)
        start_time = self._exec_start_times.pop(agent_id, None)
        if span is not None:
            span.set_attribute("openclaw.success", result.success)
            span.set_attribute("openclaw.latency_ms", result.latency_ms)
            span.set_attribute("openclaw.tokens.input", result.token_usage.input)
            span.set_attribute("openclaw.tokens.output", result.token_usage.output)
            span.set_attribute("openclaw.tokens.total", result.token_usage.total)
            span.set_attribute("openclaw.content_len", len(result.content))
            if result.stop_reason is not None:
                span.set_attribute("openclaw.stop_reason", result.stop_reason)
            if start_time is not None:
                actual_latency = int((time.monotonic() - start_time) * 1000)
                span.set_attribute("openclaw.handler_latency_ms", actual_latency)
            span.end()

    async def on_file_generated(self, agent_id: str, file: GeneratedFile) -> None:
        """Record file generation as an event on the active span."""
        if not self._available:
            return
        span = self._active_spans.get(agent_id)
        if span is not None:
            span.add_event(
                "file_generated",
                attributes={
                    "openclaw.file.name": file.name,
                    "openclaw.file.path": file.path,
                    "openclaw.file.size_bytes": file.size_bytes,
                    "openclaw.file.mime_type": file.mime_type,
                },
            )

    async def on_stream_event(self, agent_id: str, event: StreamEvent) -> None:
        """Record stream events as OTel events on the active span."""
        if not self._available:
            return
        span = self._active_spans.get(agent_id)
        if span is not None:
            span.add_event(
                f"stream:{event.event_type}",
                attributes={"openclaw.event_type": str(event.event_type)},
            )
