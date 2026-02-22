"""High-level audit logger that dispatches events to multiple sinks."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import structlog

from openclaw_sdk.audit.models import AuditEvent
from openclaw_sdk.audit.sinks import AuditSink
from openclaw_sdk.core.types import ExecutionResult

logger = structlog.get_logger(__name__)


class AuditLogger:
    """Fan-out audit dispatcher.

    Sends each :class:`AuditEvent` to every registered
    :class:`AuditSink`.  Sink failures are logged but never propagated
    to the caller.

    Example::

        audit = AuditLogger()
        audit.add_sink(InMemoryAuditSink())
        audit.add_sink(FileAuditSink("/var/log/openclaw-audit.jsonl"))
        await audit.log(AuditEvent(event_type="auth", action="login"))
    """

    def __init__(self, sinks: list[AuditSink] | None = None) -> None:
        self._sinks: list[AuditSink] = list(sinks) if sinks else []

    def add_sink(self, sink: AuditSink) -> AuditLogger:
        """Register a new sink.  Returns ``self`` for chaining."""
        self._sinks.append(sink)
        return self

    async def log(self, event: AuditEvent) -> None:
        """Dispatch *event* to all registered sinks."""
        for sink in self._sinks:
            try:
                await sink.write(event)
            except Exception:
                logger.warning(
                    "audit_sink_error",
                    sink=type(sink).__name__,
                    event_id=event.event_id,
                    exc_info=True,
                )

    async def log_execution(
        self,
        agent_id: str,
        result: ExecutionResult,
        *,
        user_id: str | None = None,
        tenant_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Convenience method to log an agent execution result."""
        cost: float | None = None
        usage = result.token_usage
        if usage.total > 0:
            # Rough estimate; callers can pass a precise cost in details.
            cost = None

        event = AuditEvent(
            event_type="execute",
            agent_id=agent_id,
            user_id=user_id,
            tenant_id=tenant_id,
            action="agent.execute",
            resource=f"agent:{agent_id}",
            success=result.success,
            error=result.error_message,
            latency_ms=result.latency_ms,
            cost_usd=cost,
            details=details or {},
        )
        await self.log(event)

    async def query(
        self,
        event_type: str | None = None,
        agent_id: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[AuditEvent]:
        """Query all sinks and merge results, limited to *limit* events.

        Results are collected from every sink that supports querying.
        Duplicates (by ``event_id``) are removed and the list is sorted
        by timestamp descending.
        """
        seen_ids: set[str] = set()
        merged: list[AuditEvent] = []
        for sink in self._sinks:
            try:
                events = await sink.query(
                    event_type=event_type,
                    agent_id=agent_id,
                    since=since,
                    limit=limit,
                )
                for ev in events:
                    if ev.event_id not in seen_ids:
                        seen_ids.add(ev.event_id)
                        merged.append(ev)
            except Exception:
                logger.warning(
                    "audit_query_error",
                    sink=type(sink).__name__,
                    exc_info=True,
                )
        merged.sort(key=lambda e: e.timestamp, reverse=True)
        return merged[:limit]

    async def close(self) -> None:
        """Close all registered sinks."""
        for sink in self._sinks:
            try:
                await sink.close()
            except Exception:
                logger.warning(
                    "audit_sink_close_error",
                    sink=type(sink).__name__,
                    exc_info=True,
                )
