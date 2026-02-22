"""Tests for audit/ — AuditEvent, sinks, and AuditLogger."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from openclaw_sdk.audit.logger import AuditLogger
from openclaw_sdk.audit.models import AuditEvent
from openclaw_sdk.audit.sinks import (
    AuditSink,
    FileAuditSink,
    InMemoryAuditSink,
    StructlogAuditSink,
)
from openclaw_sdk.core.types import ExecutionResult


# ---------------------------------------------------------------------------
# AuditEvent model
# ---------------------------------------------------------------------------


def test_audit_event_defaults() -> None:
    ev = AuditEvent(event_type="test")
    assert ev.event_type == "test"
    assert len(ev.event_id) == 16
    assert ev.success is True
    assert ev.agent_id is None
    assert ev.details == {}
    assert ev.timestamp.tzinfo is not None


def test_audit_event_full() -> None:
    ev = AuditEvent(
        event_type="execute",
        agent_id="bot-1",
        user_id="u-42",
        tenant_id="t-1",
        action="agent.execute",
        resource="agent:bot-1",
        details={"query": "hello"},
        success=False,
        error="timeout",
        cost_usd=0.003,
        latency_ms=1200,
    )
    assert ev.agent_id == "bot-1"
    assert ev.success is False
    assert ev.error == "timeout"
    assert ev.cost_usd == 0.003


# ---------------------------------------------------------------------------
# InMemoryAuditSink
# ---------------------------------------------------------------------------


async def test_in_memory_sink_write_and_query() -> None:
    sink = InMemoryAuditSink(max_entries=100)
    ev = AuditEvent(event_type="auth", agent_id="a1")
    await sink.write(ev)
    assert len(sink.events) == 1
    assert sink.events[0].event_id == ev.event_id


async def test_in_memory_sink_circular_buffer() -> None:
    sink = InMemoryAuditSink(max_entries=3)
    for i in range(5):
        await sink.write(AuditEvent(event_type="test", action=str(i)))
    assert len(sink.events) == 3
    # Oldest (0, 1) should be evicted; remaining are 2, 3, 4.
    assert [e.action for e in sink.events] == ["2", "3", "4"]


async def test_in_memory_sink_query_filters() -> None:
    sink = InMemoryAuditSink()
    await sink.write(AuditEvent(event_type="auth", agent_id="a1"))
    await sink.write(AuditEvent(event_type="execute", agent_id="a2"))
    await sink.write(AuditEvent(event_type="auth", agent_id="a2"))

    # Filter by event_type.
    results = await sink.query(event_type="auth")
    assert len(results) == 2

    # Filter by agent_id.
    results = await sink.query(agent_id="a2")
    assert len(results) == 2

    # Combined filters.
    results = await sink.query(event_type="auth", agent_id="a2")
    assert len(results) == 1


async def test_in_memory_sink_query_since() -> None:
    sink = InMemoryAuditSink()
    old_ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
    new_ts = datetime(2025, 6, 1, tzinfo=timezone.utc)
    await sink.write(AuditEvent(event_type="x", timestamp=old_ts))
    await sink.write(AuditEvent(event_type="x", timestamp=new_ts))

    cutoff = datetime(2025, 1, 1, tzinfo=timezone.utc)
    results = await sink.query(since=cutoff)
    assert len(results) == 1
    assert results[0].timestamp == new_ts


async def test_in_memory_sink_query_limit() -> None:
    sink = InMemoryAuditSink()
    for _ in range(10):
        await sink.write(AuditEvent(event_type="x"))
    results = await sink.query(limit=3)
    assert len(results) == 3


# ---------------------------------------------------------------------------
# FileAuditSink
# ---------------------------------------------------------------------------


async def test_file_sink_write_and_read(tmp_path: object) -> None:
    path = tmp_path / "audit.jsonl"  # type: ignore[operator]
    sink = FileAuditSink(path)

    ev1 = AuditEvent(event_type="auth", agent_id="a1", action="login")
    ev2 = AuditEvent(event_type="execute", agent_id="a2", action="run")
    await sink.write(ev1)
    await sink.write(ev2)

    # Verify JSONL format.
    lines = path.read_text(encoding="utf-8").strip().split("\n")  # type: ignore[union-attr]
    assert len(lines) == 2
    parsed = json.loads(lines[0])
    assert parsed["event_type"] == "auth"


async def test_file_sink_query(tmp_path: object) -> None:
    path = tmp_path / "audit.jsonl"  # type: ignore[operator]
    sink = FileAuditSink(path)

    await sink.write(AuditEvent(event_type="auth", agent_id="a1"))
    await sink.write(AuditEvent(event_type="execute", agent_id="a2"))

    results = await sink.query(event_type="auth")
    assert len(results) == 1
    assert results[0].event_type == "auth"


async def test_file_sink_query_nonexistent(tmp_path: object) -> None:
    path = tmp_path / "no-such-file.jsonl"  # type: ignore[operator]
    sink = FileAuditSink(path)
    results = await sink.query()
    assert results == []


# ---------------------------------------------------------------------------
# StructlogAuditSink
# ---------------------------------------------------------------------------


async def test_structlog_sink_write_no_error() -> None:
    """StructlogAuditSink.write should complete without raising."""
    sink = StructlogAuditSink()
    ev = AuditEvent(event_type="auth", action="login")
    await sink.write(ev)  # should not raise


# ---------------------------------------------------------------------------
# AuditLogger — multi-sink dispatch
# ---------------------------------------------------------------------------


async def test_audit_logger_dispatches_to_all_sinks() -> None:
    sink1 = InMemoryAuditSink()
    sink2 = InMemoryAuditSink()
    audit = AuditLogger(sinks=[sink1, sink2])

    ev = AuditEvent(event_type="test")
    await audit.log(ev)

    assert len(sink1.events) == 1
    assert len(sink2.events) == 1


async def test_audit_logger_add_sink_chaining() -> None:
    audit = AuditLogger()
    sink = InMemoryAuditSink()
    returned = audit.add_sink(sink)
    assert returned is audit

    await audit.log(AuditEvent(event_type="test"))
    assert len(sink.events) == 1


async def test_audit_logger_log_execution() -> None:
    sink = InMemoryAuditSink()
    audit = AuditLogger(sinks=[sink])

    result = ExecutionResult(success=True, content="done", latency_ms=500)
    await audit.log_execution("bot-1", result, user_id="u-1")

    events = sink.events
    assert len(events) == 1
    assert events[0].event_type == "execute"
    assert events[0].agent_id == "bot-1"
    assert events[0].user_id == "u-1"
    assert events[0].latency_ms == 500


async def test_audit_logger_query_merges_sinks() -> None:
    sink1 = InMemoryAuditSink()
    sink2 = InMemoryAuditSink()
    audit = AuditLogger(sinks=[sink1, sink2])

    ev1 = AuditEvent(event_type="auth", timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc))
    ev2 = AuditEvent(event_type="execute", timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc))
    await sink1.write(ev1)
    await sink2.write(ev2)

    results = await audit.query()
    assert len(results) == 2
    # Sorted by timestamp descending.
    assert results[0].timestamp > results[1].timestamp


async def test_audit_logger_close() -> None:
    sink = InMemoryAuditSink()
    audit = AuditLogger(sinks=[sink])
    await audit.close()  # should not raise


async def test_audit_logger_sink_error_does_not_propagate() -> None:
    """If a sink raises during write, the error is swallowed."""

    class BrokenSink(AuditSink):
        async def write(self, event: AuditEvent) -> None:
            raise RuntimeError("boom")

    good_sink = InMemoryAuditSink()
    audit = AuditLogger(sinks=[BrokenSink(), good_sink])

    await audit.log(AuditEvent(event_type="test"))
    # The good sink should still have received the event.
    assert len(good_sink.events) == 1
