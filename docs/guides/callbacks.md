# Callbacks & Observability

Callbacks let you hook into the agent execution lifecycle to log events, collect metrics, trace spans, and build custom observability. The SDK provides a `CallbackHandler` base class that you subclass, plus built-in handlers for common patterns.

## CallbackHandler

The `CallbackHandler` base class defines hooks that are called at various points during execution. Override any method you need:

```python
import asyncio
from openclaw_sdk import OpenClawClient, ExecutionResult
from openclaw_sdk.callbacks.handler import CallbackHandler

class MyHandler(CallbackHandler):
    async def on_execution_start(self, agent_id: str, query: str) -> None:
        print(f"[START] Agent {agent_id}: {query[:50]}...")

    async def on_execution_end(self, agent_id: str, result: ExecutionResult) -> None:
        print(f"[END] Agent {agent_id}: {result.latency_ms:.0f}ms, "
              f"{result.token_usage.total} tokens")

    async def on_tool_call(self, agent_id: str, tool_name: str, tool_input: dict) -> None:
        print(f"[TOOL] Agent {agent_id} calling {tool_name}")

    async def on_tool_result(
        self, agent_id: str, tool_name: str, output: str, duration_ms: float
    ) -> None:
        print(f"[TOOL] {tool_name} returned in {duration_ms:.0f}ms")

    async def on_error(self, agent_id: str, error: Exception) -> None:
        print(f"[ERROR] Agent {agent_id}: {error}")

async def main():
    async with OpenClawClient.connect(
        "ws://127.0.0.1:18789/gateway",
        callbacks=MyHandler(),
    ) as client:
        agent = client.get_agent("my-agent")
        result = await agent.execute("What is 2 + 2?")
        print(result.content)

asyncio.run(main())
```

## All Available Hooks

| Method | Called When |
|---|---|
| `on_execution_start(agent_id, query)` | An execution begins |
| `on_execution_end(agent_id, result)` | An execution completes (success or failure) |
| `on_stream_event(agent_id, event)` | A streaming event is received |
| `on_tool_call(agent_id, tool_name, tool_input)` | The agent invokes a tool |
| `on_tool_result(agent_id, tool_name, output, duration_ms)` | A tool returns its result |
| `on_file_generated(agent_id, file)` | The agent generates a file |
| `on_error(agent_id, error)` | An error occurs during execution |

All hooks are async and have default no-op implementations, so you only need to override the ones you care about.

## LoggingCallbackHandler

The SDK includes a `LoggingCallbackHandler` that emits structured log messages via `structlog` for every lifecycle event. This is useful for debugging and production logging.

```python
import asyncio
from openclaw_sdk import OpenClawClient
from openclaw_sdk.callbacks.handler import LoggingCallbackHandler

async def main():
    handler = LoggingCallbackHandler()

    async with OpenClawClient.connect(
        "ws://127.0.0.1:18789/gateway",
        callbacks=handler,
    ) as client:
        agent = client.get_agent("my-agent")
        result = await agent.execute("Summarize the latest news")
        print(result.content)

asyncio.run(main())
```

!!! tip
    `LoggingCallbackHandler` uses `structlog` under the hood. Configure structlog's processors and output format in your application startup to control how callback logs appear (JSON, console, etc.).

## CompositeCallbackHandler

When you need multiple handlers active at the same time (e.g., logging and metrics), use `CompositeCallbackHandler` to combine them. Each event is dispatched to all registered handlers.

```python
import asyncio
from openclaw_sdk import OpenClawClient, ExecutionResult
from openclaw_sdk.callbacks.handler import (
    CallbackHandler,
    CompositeCallbackHandler,
    LoggingCallbackHandler,
)

class MetricsHandler(CallbackHandler):
    def __init__(self) -> None:
        self.total_calls = 0
        self.total_tokens = 0
        self.errors = 0

    async def on_execution_end(self, agent_id: str, result: ExecutionResult) -> None:
        self.total_calls += 1
        self.total_tokens += result.token_usage.total

    async def on_error(self, agent_id: str, error: Exception) -> None:
        self.errors += 1

async def main():
    metrics = MetricsHandler()
    composite = CompositeCallbackHandler([
        LoggingCallbackHandler(),
        metrics,
    ])

    async with OpenClawClient.connect(
        "ws://127.0.0.1:18789/gateway",
        callbacks=composite,
    ) as client:
        agent = client.get_agent("my-agent")

        queries = ["What is AI?", "Explain ML.", "Define NLP."]
        for q in queries:
            await agent.execute(q)

        print(f"Total calls: {metrics.total_calls}")
        print(f"Total tokens: {metrics.total_tokens}")
        print(f"Errors: {metrics.errors}")

asyncio.run(main())
```

## Client-Level vs Per-Call Callbacks

Callbacks can be attached at two levels:

**Client-level** — passed to `OpenClawClient.connect()`, applies to every execution on that client.

```python
async with OpenClawClient.connect(
    "ws://127.0.0.1:18789/gateway",
    callbacks=MyHandler(),
) as client:
    # MyHandler is invoked for all agent calls on this client
    agent = client.get_agent("my-agent")
    await agent.execute("Hello")
```

**Per-call** — passed to individual `execute()` or `execute_stream()` calls for fine-grained control.

```python
result = await agent.execute("Sensitive query", callbacks=AuditHandler())
```

!!! note
    When both client-level and per-call callbacks are set, both are invoked. Client-level callbacks fire first, then per-call callbacks.

## Tracing

For hierarchical observability, the SDK provides a tracing system built on `Tracer`, `Span`, and `TracingCallbackHandler`. Traces capture the full execution tree with timing, token counts, and nested spans for tool calls.

### Setting Up Tracing

```python
import asyncio
from openclaw_sdk import OpenClawClient
from openclaw_sdk.callbacks.handler import TracingCallbackHandler, Tracer

async def main():
    tracer = Tracer()
    tracing_handler = TracingCallbackHandler(tracer)

    async with OpenClawClient.connect(
        "ws://127.0.0.1:18789/gateway",
        callbacks=tracing_handler,
    ) as client:
        agent = client.get_agent("my-agent")

        await agent.execute("Research quantum computing")
        await agent.execute("Summarize the findings")

        # Export traces as JSON for analysis
        trace_data = tracer.export_json()
        print(trace_data)

asyncio.run(main())
```

### Understanding Spans

Each execution creates a root `Span`. Tool calls within that execution create child spans. The span hierarchy looks like:

```
Span: execute "Research quantum computing" (3200ms)
  Span: tool_call "web_search" (1200ms)
  Span: tool_call "read_file" (80ms)
Span: execute "Summarize the findings" (1100ms)
```

### Exporting Traces

`tracer.export_json()` returns a JSON string with all collected spans. You can write this to a file, send it to a tracing backend, or parse it for custom analysis.

```python
import json

trace_data = tracer.export_json()
traces = json.loads(trace_data)

for span in traces:
    indent = "  " * span.get("depth", 0)
    print(f"{indent}{span['name']} ({span['duration_ms']:.0f}ms)")
```

!!! tip
    For production observability, feed trace data into OpenTelemetry, Datadog, or your preferred APM tool. The exported JSON format is straightforward to map to OTLP spans.

## Building a Custom Handler

Here is a complete example of a custom handler that tracks per-agent statistics and writes a summary report:

```python
import asyncio
from collections import defaultdict
from openclaw_sdk import OpenClawClient, ExecutionResult
from openclaw_sdk.callbacks.handler import CallbackHandler

class AgentStatsHandler(CallbackHandler):
    def __init__(self) -> None:
        self.stats: dict[str, dict] = defaultdict(
            lambda: {"calls": 0, "tokens": 0, "errors": 0, "tools": 0, "latency": 0.0}
        )

    async def on_execution_end(self, agent_id: str, result: ExecutionResult) -> None:
        s = self.stats[agent_id]
        s["calls"] += 1
        s["tokens"] += result.token_usage.total
        s["latency"] += result.latency_ms

    async def on_tool_call(self, agent_id: str, tool_name: str, tool_input: dict) -> None:
        self.stats[agent_id]["tools"] += 1

    async def on_error(self, agent_id: str, error: Exception) -> None:
        self.stats[agent_id]["errors"] += 1

    def report(self) -> str:
        lines = ["Agent Statistics", "=" * 40]
        for agent_id, s in self.stats.items():
            avg_latency = s["latency"] / s["calls"] if s["calls"] else 0
            lines.append(f"\n{agent_id}:")
            lines.append(f"  Calls:       {s['calls']}")
            lines.append(f"  Tokens:      {s['tokens']}")
            lines.append(f"  Tool calls:  {s['tools']}")
            lines.append(f"  Errors:      {s['errors']}")
            lines.append(f"  Avg latency: {avg_latency:.0f}ms")
        return "\n".join(lines)

async def main():
    stats = AgentStatsHandler()

    async with OpenClawClient.connect(
        "ws://127.0.0.1:18789/gateway",
        callbacks=stats,
    ) as client:
        agent = client.get_agent("my-agent")
        await agent.execute("Task 1")
        await agent.execute("Task 2")
        await agent.execute("Task 3")

    print(stats.report())

asyncio.run(main())
```
