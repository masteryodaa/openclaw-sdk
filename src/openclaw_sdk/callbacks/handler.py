from __future__ import annotations

from abc import ABC
from typing import Any

import structlog

from openclaw_sdk.core.types import ExecutionResult, GeneratedFile, StreamEvent, TokenUsage

logger = structlog.get_logger(__name__)


class CallbackHandler(ABC):
    """Override any methods to inject custom logic. All have default no-op implementations."""

    async def on_execution_start(self, agent_id: str, query: str) -> None:
        pass

    async def on_llm_start(self, agent_id: str, prompt: str, model: str) -> None:
        pass

    async def on_llm_end(
        self,
        agent_id: str,
        response: str,
        token_usage: TokenUsage,
        duration_ms: int,
    ) -> None:
        pass

    async def on_tool_call(
        self, agent_id: str, tool_name: str, tool_input: str
    ) -> None:
        pass

    async def on_tool_result(
        self, agent_id: str, tool_name: str, result: str, duration_ms: int
    ) -> None:
        pass

    async def on_file_generated(self, agent_id: str, file: GeneratedFile) -> None:
        pass

    async def on_execution_end(self, agent_id: str, result: ExecutionResult) -> None:
        pass

    async def on_error(self, agent_id: str, error: Exception) -> None:
        pass

    async def on_stream_event(self, agent_id: str, event: StreamEvent) -> None:
        pass


class LoggingCallbackHandler(CallbackHandler):
    """Logs all events via structlog."""

    async def on_execution_start(self, agent_id: str, query: str) -> None:
        logger.info("execution_start", agent_id=agent_id, query=query)

    async def on_llm_start(self, agent_id: str, prompt: str, model: str) -> None:
        logger.info("llm_start", agent_id=agent_id, model=model, prompt_len=len(prompt))

    async def on_llm_end(
        self,
        agent_id: str,
        response: str,
        token_usage: TokenUsage,
        duration_ms: int,
    ) -> None:
        logger.info(
            "llm_end",
            agent_id=agent_id,
            input_tokens=token_usage.input,
            output_tokens=token_usage.output,
            duration_ms=duration_ms,
        )

    async def on_tool_call(
        self, agent_id: str, tool_name: str, tool_input: str
    ) -> None:
        logger.info("tool_call", agent_id=agent_id, tool_name=tool_name, tool_input=tool_input)

    async def on_tool_result(
        self, agent_id: str, tool_name: str, result: str, duration_ms: int
    ) -> None:
        logger.info(
            "tool_result",
            agent_id=agent_id,
            tool_name=tool_name,
            result_len=len(result),
            duration_ms=duration_ms,
        )

    async def on_file_generated(self, agent_id: str, file: GeneratedFile) -> None:
        logger.info(
            "file_generated",
            agent_id=agent_id,
            name=file.name,
            path=file.path,
            size_bytes=file.size_bytes,
        )

    async def on_execution_end(self, agent_id: str, result: ExecutionResult) -> None:
        logger.info(
            "execution_end",
            agent_id=agent_id,
            success=result.success,
            latency_ms=result.latency_ms,
        )

    async def on_error(self, agent_id: str, error: Exception) -> None:
        logger.error("execution_error", agent_id=agent_id, error=str(error), exc_info=error)

    async def on_stream_event(self, agent_id: str, event: StreamEvent) -> None:
        logger.debug(
            "stream_event",
            agent_id=agent_id,
            event_type=event.event_type,
        )


class CostCallbackHandler(CallbackHandler):
    """Automatically records execution costs into a :class:`CostTracker`.

    Attach to a client or pass per-call to track LLM spending automatically.

    Args:
        tracker: The :class:`CostTracker` instance to record costs into.
        model: Default model name used for cost calculation.
    """

    def __init__(self, tracker: Any, model: str = "claude-sonnet-4-20250514") -> None:
        self._tracker = tracker
        self._model = model
        self._current_query: str = ""

    async def on_execution_start(self, agent_id: str, query: str) -> None:
        self._current_query = query

    async def on_execution_end(self, agent_id: str, result: ExecutionResult) -> None:
        self._tracker.record(
            result,
            agent_id=agent_id,
            model=self._model,
            query=self._current_query,
        )


class CompositeCallbackHandler(CallbackHandler):
    """Fans out all callback calls to multiple handlers.

    Each handler is called in order. Exceptions from individual handlers are
    caught and logged so one failing handler does not block the others.
    """

    def __init__(self, handlers: list[CallbackHandler]) -> None:
        self._handlers = list(handlers)

    async def on_execution_start(self, agent_id: str, query: str) -> None:
        for handler in self._handlers:
            try:
                await handler.on_execution_start(agent_id, query)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "callback_handler_error",
                    callback_event="on_execution_start",
                    handler=type(handler).__name__,
                    error=str(exc),
                )

    async def on_llm_start(self, agent_id: str, prompt: str, model: str) -> None:
        for handler in self._handlers:
            try:
                await handler.on_llm_start(agent_id, prompt, model)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "callback_handler_error",
                    callback_event="on_llm_start",
                    handler=type(handler).__name__,
                    error=str(exc),
                )

    async def on_llm_end(
        self,
        agent_id: str,
        response: str,
        token_usage: TokenUsage,
        duration_ms: int,
    ) -> None:
        for handler in self._handlers:
            try:
                await handler.on_llm_end(agent_id, response, token_usage, duration_ms)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "callback_handler_error",
                    callback_event="on_llm_end",
                    handler=type(handler).__name__,
                    error=str(exc),
                )

    async def on_tool_call(
        self, agent_id: str, tool_name: str, tool_input: str
    ) -> None:
        for handler in self._handlers:
            try:
                await handler.on_tool_call(agent_id, tool_name, tool_input)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "callback_handler_error",
                    callback_event="on_tool_call",
                    handler=type(handler).__name__,
                    error=str(exc),
                )

    async def on_tool_result(
        self, agent_id: str, tool_name: str, result: str, duration_ms: int
    ) -> None:
        for handler in self._handlers:
            try:
                await handler.on_tool_result(agent_id, tool_name, result, duration_ms)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "callback_handler_error",
                    callback_event="on_tool_result",
                    handler=type(handler).__name__,
                    error=str(exc),
                )

    async def on_file_generated(self, agent_id: str, file: GeneratedFile) -> None:
        for handler in self._handlers:
            try:
                await handler.on_file_generated(agent_id, file)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "callback_handler_error",
                    callback_event="on_file_generated",
                    handler=type(handler).__name__,
                    error=str(exc),
                )

    async def on_execution_end(self, agent_id: str, result: ExecutionResult) -> None:
        for handler in self._handlers:
            try:
                await handler.on_execution_end(agent_id, result)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "callback_handler_error",
                    callback_event="on_execution_end",
                    handler=type(handler).__name__,
                    error=str(exc),
                )

    async def on_error(self, agent_id: str, error: Exception) -> None:
        for handler in self._handlers:
            try:
                await handler.on_error(agent_id, error)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "callback_handler_error",
                    callback_event="on_error",
                    handler=type(handler).__name__,
                    error=str(exc),
                )

    async def on_stream_event(self, agent_id: str, event: StreamEvent) -> None:
        for handler in self._handlers:
            try:
                await handler.on_stream_event(agent_id, event)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "callback_handler_error",
                    callback_event="on_stream_event",
                    handler=type(handler).__name__,
                    error=str(exc),
                )
