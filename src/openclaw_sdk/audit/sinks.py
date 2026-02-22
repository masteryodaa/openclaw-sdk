"""Pluggable audit sinks: in-memory, file (JSONL), and structlog."""

from __future__ import annotations

import asyncio
import json
from abc import ABC, abstractmethod
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

from openclaw_sdk.audit.models import AuditEvent

logger = structlog.get_logger(__name__)


class AuditSink(ABC):
    """Abstract base for audit event sinks.

    Subclass this to ship audit events to external systems (e.g. S3,
    Elasticsearch, a database).
    """

    @abstractmethod
    async def write(self, event: AuditEvent) -> None:
        """Persist a single audit event."""

    async def query(
        self,
        event_type: str | None = None,
        agent_id: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[AuditEvent]:
        """Return matching events.  Default implementation returns an empty list."""
        return []

    async def close(self) -> None:
        """Release resources held by the sink."""


class InMemoryAuditSink(AuditSink):
    """Circular-buffer sink backed by :class:`collections.deque`.

    Args:
        max_entries: Maximum number of events to retain (default 10 000).
    """

    def __init__(self, max_entries: int = 10000) -> None:
        self._max_entries = max_entries
        self._events: deque[AuditEvent] = deque(maxlen=max_entries)

    async def write(self, event: AuditEvent) -> None:
        self._events.append(event)

    async def query(
        self,
        event_type: str | None = None,
        agent_id: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[AuditEvent]:
        results: list[AuditEvent] = []
        for ev in reversed(self._events):
            if event_type is not None and ev.event_type != event_type:
                continue
            if agent_id is not None and ev.agent_id != agent_id:
                continue
            if since is not None and ev.timestamp < since:
                continue
            results.append(ev)
            if len(results) >= limit:
                break
        return results

    @property
    def events(self) -> list[AuditEvent]:
        """Return all stored events (oldest first)."""
        return list(self._events)


class FileAuditSink(AuditSink):
    """Append-only JSONL file sink.

    Uses :func:`asyncio.to_thread` so file I/O does not block the event
    loop.

    Args:
        path: Filesystem path for the JSONL audit log.
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def _serialize(self, event: AuditEvent) -> str:
        """Serialize an event to a single JSON line."""
        data: dict[str, Any] = event.model_dump(mode="json")
        return json.dumps(data, default=str, sort_keys=True)

    def _write_sync(self, line: str) -> None:
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    async def write(self, event: AuditEvent) -> None:
        line = self._serialize(event)
        await asyncio.to_thread(self._write_sync, line)

    async def query(
        self,
        event_type: str | None = None,
        agent_id: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[AuditEvent]:
        """Read events from the JSONL file and filter."""
        if not self._path.exists():
            return []

        def _read() -> list[AuditEvent]:
            results: list[AuditEvent] = []
            with self._path.open("r", encoding="utf-8") as fh:
                for raw_line in fh:
                    raw_line = raw_line.strip()
                    if not raw_line:
                        continue
                    ev = AuditEvent.model_validate_json(raw_line)
                    if event_type is not None and ev.event_type != event_type:
                        continue
                    if agent_id is not None and ev.agent_id != agent_id:
                        continue
                    if since is not None and ev.timestamp < since:
                        continue
                    results.append(ev)
                    if len(results) >= limit:
                        break
            return results

        return await asyncio.to_thread(_read)


class StructlogAuditSink(AuditSink):
    """Sink that emits each event via :mod:`structlog`."""

    def __init__(self, log_level: str = "info") -> None:
        self._log_level = log_level
        self._logger = structlog.get_logger("openclaw_sdk.audit")

    async def write(self, event: AuditEvent) -> None:
        log_fn = getattr(self._logger, self._log_level, self._logger.info)
        log_fn(
            "audit_event",
            event_id=event.event_id,
            event_type=event.event_type,
            agent_id=event.agent_id,
            action=event.action,
            resource=event.resource,
            success=event.success,
            error=event.error,
        )
