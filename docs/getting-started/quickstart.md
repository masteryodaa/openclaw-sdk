# Quickstart

This guide takes you from zero to a working OpenClaw integration in under 5 minutes.

## Prerequisites

- Python 3.11+
- OpenClaw running locally (default: `ws://127.0.0.1:18789/gateway`) or remotely

## 1. Install

```bash
pip install openclaw-sdk
```

## 2. Verify Connection

```python
import asyncio
from openclaw_sdk import OpenClawClient

async def main():
    async with OpenClawClient.connect() as client:
        status = await client.health()
        print("Healthy:", status.healthy)
        print("Version:", status.version)

asyncio.run(main())
```

If the output is `Healthy: True`, you're connected and ready.

!!! tip "Auto-Detection"
    `OpenClawClient.connect()` auto-detects your gateway:

    1. `OPENCLAW_GATEWAY_WS_URL` env var (WebSocket)
    2. `OPENCLAW_OPENAI_BASE_URL` env var (OpenAI-compatible HTTP)
    3. Local socket probe at `127.0.0.1:18789`

## 3. Execute Your First Agent

```python
import asyncio
from openclaw_sdk import OpenClawClient

async def main():
    async with OpenClawClient.connect() as client:
        agent = client.get_agent("my-agent")
        result = await agent.execute("Hello, what can you do?")
        print(result.content)
        print(f"Latency: {result.latency_ms}ms")

asyncio.run(main())
```

!!! note
    `get_agent(agent_id)` does not make a network call — it creates a lightweight
    handle. The actual gateway call happens when you call `execute()`.

## 4. Session Management

Every agent call belongs to a **session** — a named conversation thread stored in OpenClaw. The default session name is `"main"`.

```python
# Two separate sessions for the same agent:
agent_a = client.get_agent("bot", session_name="alice")
agent_b = client.get_agent("bot", session_name="bob")

print(agent_a.session_key)  # "agent:bot:alice"
print(agent_b.session_key)  # "agent:bot:bob"
```

## 5. Streaming Responses

Use `execute_stream()` to receive events as they arrive:

```python
import asyncio
from openclaw_sdk import OpenClawClient
from openclaw_sdk.core.constants import EventType

async def main():
    async with OpenClawClient.connect() as client:
        agent = client.get_agent("writer-bot")
        stream = await agent.execute_stream("Tell me a short story")
        async for event in stream:
            if event.event_type == EventType.CONTENT:
                print(event.data["payload"]["content"], end="", flush=True)
        print()

asyncio.run(main())
```

## 6. Structured Output

Extract validated Pydantic models from LLM responses:

```python
import asyncio
from pydantic import BaseModel
from openclaw_sdk import OpenClawClient
from openclaw_sdk.output.structured import StructuredOutput

class Sentiment(BaseModel):
    label: str         # "positive", "negative", "neutral"
    confidence: float

async def main():
    async with OpenClawClient.connect() as client:
        agent = client.get_agent("analyst-bot")
        result = await StructuredOutput.execute(
            agent,
            "Analyse the sentiment of: 'I love this product!'",
            Sentiment,
            max_retries=2,
        )
        print(f"{result.label} ({result.confidence:.0%})")

asyncio.run(main())
```

## 7. Idempotency

Prevent duplicate executions when retrying:

```python
result = await agent.execute(
    "Process order #12345",
    idempotency_key="order-12345-process-v1",
)
```

OpenClaw returns the same result for the same key without re-running the agent.

## 8. Timeouts

Override the default timeout (300s) per call:

```python
from openclaw_sdk import ExecutionOptions

result = await agent.execute(
    "Run a long analysis",
    options=ExecutionOptions(timeout_seconds=600),
)
```

## 9. Callbacks

Hook into the execution lifecycle:

```python
from openclaw_sdk.callbacks.handler import CallbackHandler
from openclaw_sdk.core.types import ExecutionResult

class MyCallback(CallbackHandler):
    async def on_execution_start(self, agent_id: str, query: str) -> None:
        print(f"[START] {agent_id}: {query[:50]}")

    async def on_execution_end(self, agent_id: str, result: ExecutionResult) -> None:
        print(f"[DONE]  {agent_id}: {result.latency_ms}ms")

async with OpenClawClient.connect(callbacks=[MyCallback()]) as client:
    await client.get_agent("bot").execute("hello")
```

## 10. Pipelines

Chain agents where each step feeds the next:

```python
from openclaw_sdk.pipeline.pipeline import Pipeline

async with OpenClawClient.connect() as client:
    result = await (
        Pipeline(client)
        .add_step("researcher", "research-bot", "Research: {topic}")
        .add_step("writer", "writer-bot", "Write based on: {researcher}")
        .run(topic="quantum computing")
    )
    print(result.final_result.content)
```

## Next Steps

- [Configuration](configuration.md) — all config options and env vars
- [Agents & Execution](../guides/agents.md) — deep dive into agent features
- [Streaming](../guides/streaming.md) — real-time event processing
- [API Reference](../api/client.md) — complete API documentation
