# Audit Logging

The OpenClaw SDK provides an audit logging system for recording a tamper-evident
trail of every notable action: agent executions, configuration changes,
authentication events, and more. Events are dispatched to one or more pluggable
sinks (in-memory, JSONL file, structlog) and can be queried back with
filtering support.

## Quick Start

```python
import asyncio

from openclaw_sdk import OpenClawClient
from openclaw_sdk.audit import (
    AuditEvent,
    AuditLogger,
    FileAuditSink,
    InMemoryAuditSink,
)


async def main():
    # Create sinks
    memory_sink = InMemoryAuditSink(max_entries=5000)
    file_sink = FileAuditSink("audit.jsonl")

    # Wire up the logger
    audit = AuditLogger()
    audit.add_sink(memory_sink)
    audit.add_sink(file_sink)

    # Log a custom event
    await audit.log(AuditEvent(
        event_type="auth",
        action="login",
        user_id="user-42",
        details={"method": "api_key"},
    ))

    # Log an agent execution result
    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        agent = client.get_agent("assistant")
        result = await agent.execute("Hello")

        await audit.log_execution("assistant", result, user_id="user-42")

    # Query recent events
    events = await audit.query(event_type="execute", limit=10)
    for ev in events:
        print(f"[{ev.timestamp}] {ev.event_type}: {ev.action} (success={ev.success})")

    await audit.close()

asyncio.run(main())
```

## AuditEvent

`AuditEvent` is an immutable Pydantic model that captures a single auditable
action. Every event is assigned a unique ID and a UTC timestamp automatically.

```python
from openclaw_sdk.audit import AuditEvent

event = AuditEvent(
    event_type="config_change",
    agent_id="assistant",
    user_id="admin-1",
    tenant_id="tenant-acme",
    action="config.patch",
    resource="agent:assistant",
    details={"field": "temperature", "old": 0.7, "new": 0.9},
    success=True,
)
```

| Field        | Type               | Default        | Description                                       |
|--------------|--------------------|----------------|---------------------------------------------------|
| `event_id`   | `str`              | Auto-generated | 16-character hex identifier                       |
| `event_type` | `str`              | --             | Category: `"execute"`, `"auth"`, `"config_change"` |
| `timestamp`  | `datetime`         | Now (UTC)      | When the event occurred                           |
| `agent_id`   | `str \| None`      | `None`         | Agent involved, if any                            |
| `user_id`    | `str \| None`      | `None`         | User who performed the action                     |
| `tenant_id`  | `str \| None`      | `None`         | Tenant scope for multi-tenant deployments         |
| `action`     | `str`              | `""`           | Specific action performed (e.g. `"agent.execute"`) |
| `resource`   | `str`              | `""`           | Resource affected (e.g. `"agent:assistant"`)      |
| `details`    | `dict[str, Any]`   | `{}`           | Arbitrary key-value context                       |
| `success`    | `bool`             | `True`         | Whether the action succeeded                      |
| `error`      | `str \| None`      | `None`         | Error message on failure                          |
| `cost_usd`   | `float \| None`    | `None`         | Estimated cost in USD                             |
| `latency_ms` | `int \| None`      | `None`         | Execution latency in milliseconds                 |

## Audit Sinks

Sinks persist audit events to storage backends. All sinks extend the `AuditSink`
ABC, which requires a `write()` method and optionally supports `query()` and
`close()`.

```python
from openclaw_sdk.audit import AuditSink, AuditEvent

class MyCustomSink(AuditSink):
    async def write(self, event: AuditEvent) -> None:
        """Persist the event (required)."""
        ...

    async def query(
        self,
        event_type: str | None = None,
        agent_id: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[AuditEvent]:
        """Return matching events (optional, defaults to empty list)."""
        ...

    async def close(self) -> None:
        """Release resources (optional)."""
        ...
```

### InMemoryAuditSink

A circular-buffer sink backed by `collections.deque`. Fast and query-capable,
but data is lost on process restart. Ideal for development, testing, and
short-lived applications.

```python
from openclaw_sdk.audit import InMemoryAuditSink

sink = InMemoryAuditSink(max_entries=10000)
```

| Parameter     | Type  | Default  | Description                           |
|---------------|-------|----------|---------------------------------------|
| `max_entries` | `int` | `10000`  | Maximum events retained (oldest evicted) |

The sink supports full query filtering and exposes an `events` property that
returns all stored events (oldest first):

```python
# Query filtered events
recent = await sink.query(event_type="execute", agent_id="assistant", limit=50)

# Access all raw events
all_events = sink.events
```

!!! tip "Great for testing"
    `InMemoryAuditSink` is the fastest sink and supports all query parameters.
    Use it in unit tests to assert that specific audit events were recorded.

### FileAuditSink

Appends events as JSON lines (JSONL) to a file. File I/O is offloaded to a
thread via `asyncio.to_thread` so it never blocks the event loop.

```python
from openclaw_sdk.audit import FileAuditSink

sink = FileAuditSink("logs/audit.jsonl")
```

| Parameter | Type            | Default | Description                  |
|-----------|-----------------|---------|------------------------------|
| `path`    | `str \| Path`   | --      | Filesystem path for the JSONL file |

Each line in the file is a complete JSON object that can be parsed independently:

```json
{"action":"agent.execute","agent_id":"assistant","cost_usd":null,"details":{},"error":null,"event_id":"a1b2c3d4e5f6","event_type":"execute","latency_ms":1200,"resource":"agent:assistant","success":true,"tenant_id":null,"timestamp":"2026-02-22T10:30:00+00:00","user_id":"user-42"}
```

The `FileAuditSink` also supports `query()`, which reads the file back and
filters in memory. For high-volume production use, consider a database-backed
custom sink instead.

!!! warning "Append-only"
    The file sink only appends -- it never truncates or rotates the file. Use
    external log rotation (e.g. `logrotate`) for long-running applications.

### StructlogAuditSink

Emits audit events through `structlog`, integrating with your existing
structured logging pipeline. No file or state is maintained.

```python
from openclaw_sdk.audit import StructlogAuditSink

sink = StructlogAuditSink(log_level="info")
```

| Parameter   | Type  | Default  | Description                              |
|-------------|-------|----------|------------------------------------------|
| `log_level` | `str` | `"info"` | structlog level (`"debug"`, `"info"`, `"warning"`, etc.) |

!!! note "No query support"
    `StructlogAuditSink` does not support `query()` since it delegates to the
    logging system. Pair it with a queryable sink if you need event retrieval.

## AuditLogger

`AuditLogger` is the high-level dispatcher that fans out each event to every
registered sink. Sink failures are logged but never propagated, ensuring that
one broken sink cannot block event recording for others.

```python
from openclaw_sdk.audit import AuditLogger, InMemoryAuditSink, FileAuditSink

audit = AuditLogger()
audit.add_sink(InMemoryAuditSink())
audit.add_sink(FileAuditSink("/var/log/openclaw-audit.jsonl"))
```

You can also pass sinks at construction time:

```python
audit = AuditLogger(sinks=[
    InMemoryAuditSink(),
    FileAuditSink("/var/log/openclaw-audit.jsonl"),
])
```

| Method                    | Returns             | Description                                |
|---------------------------|---------------------|--------------------------------------------|
| `add_sink(sink)`          | `AuditLogger`       | Register a sink (chainable)                |
| `log(event)`              | `None`              | Dispatch an event to all sinks             |
| `log_execution(...)`      | `None`              | Convenience: log an `ExecutionResult`      |
| `query(...)`              | `list[AuditEvent]`  | Query all sinks and merge results          |
| `close()`                 | `None`              | Close all registered sinks                 |

### Logging Events

Use `log()` for custom events and `log_execution()` for agent execution results:

```python
# Custom event
await audit.log(AuditEvent(
    event_type="auth",
    action="token_refresh",
    user_id="user-42",
))

# Execution result (convenience method)
await audit.log_execution(
    agent_id="assistant",
    result=execution_result,
    user_id="user-42",
    tenant_id="tenant-acme",
    details={"query": "Summarize this document"},
)
```

The `log_execution()` method automatically populates `event_type`, `action`,
`resource`, `success`, `error`, and `latency_ms` from the `ExecutionResult`.

| Parameter   | Type                     | Default | Description                     |
|-------------|--------------------------|---------|---------------------------------|
| `agent_id`  | `str`                    | --      | Agent that was executed         |
| `result`    | `ExecutionResult`        | --      | The execution result to log     |
| `user_id`   | `str \| None`            | `None`  | User who initiated the call     |
| `tenant_id` | `str \| None`            | `None`  | Tenant scope                    |
| `details`   | `dict[str, Any] \| None` | `None`  | Additional context              |

### Querying Events

`query()` collects results from all sinks, deduplicates by `event_id`, and
returns them sorted by timestamp (newest first):

```python
from datetime import datetime, timezone, timedelta

# All events of a given type
auth_events = await audit.query(event_type="auth")

# Events for a specific agent since a point in time
since = datetime.now(timezone.utc) - timedelta(hours=1)
recent = await audit.query(agent_id="assistant", since=since, limit=50)
```

| Parameter    | Type               | Default | Description                        |
|--------------|--------------------|---------|------------------------------------|
| `event_type` | `str \| None`      | `None`  | Filter by event type               |
| `agent_id`   | `str \| None`      | `None`  | Filter by agent ID                 |
| `since`      | `datetime \| None` | `None`  | Only return events after this time |
| `limit`      | `int`              | `100`   | Maximum number of events returned  |

## Full Example: Multi-Sink Audit Trail

```python
import asyncio
from datetime import datetime, timezone, timedelta

from openclaw_sdk import OpenClawClient
from openclaw_sdk.audit import (
    AuditEvent,
    AuditLogger,
    FileAuditSink,
    InMemoryAuditSink,
    StructlogAuditSink,
)


async def main():
    # Set up a multi-sink logger
    memory = InMemoryAuditSink(max_entries=10000)
    audit = (
        AuditLogger()
        .add_sink(memory)
        .add_sink(FileAuditSink("audit.jsonl"))
        .add_sink(StructlogAuditSink(log_level="info"))
    )

    # Record authentication
    await audit.log(AuditEvent(
        event_type="auth",
        action="login",
        user_id="admin-1",
        tenant_id="acme-corp",
    ))

    # Execute agent calls and record them
    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        agent = client.get_agent("assistant")

        for query in ["Hello", "Summarize this", "Translate to Spanish"]:
            result = await agent.execute(query)
            await audit.log_execution(
                "assistant", result,
                user_id="admin-1",
                tenant_id="acme-corp",
                details={"query": query},
            )

    # Query the audit trail
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    events = await audit.query(since=one_hour_ago, limit=20)
    print(f"Found {len(events)} audit events in the last hour")

    for ev in events:
        status = "OK" if ev.success else f"FAIL: {ev.error}"
        print(f"  [{ev.event_type}] {ev.action} - {status}")

    # Clean up
    await audit.close()

asyncio.run(main())
```
