# Quickstart — openclaw-sdk

This guide walks you from zero to a working OpenClaw integration in Python.

## Prerequisites

- Python 3.11 or newer
- An OpenClaw instance running locally or accessible via network
  - Default local address: `ws://127.0.0.1:18789/gateway`
  - Or set `OPENCLAW_GATEWAY_WS_URL` environment variable

## 1. Install

```bash
pip install openclaw-sdk
```

## 2. Verify connection

```python
import asyncio
from openclaw_sdk import OpenClawClient

async def main():
    async with OpenClawClient.connect() as client:
        status = await client.health()
        print("Healthy:", status.healthy)

asyncio.run(main())
```

If the output is `Healthy: True` you are connected and ready.

## 3. Execute your first agent

```python
import asyncio
from openclaw_sdk import OpenClawClient

async def main():
    async with OpenClawClient.connect() as client:
        agent = client.get_agent("my-agent")
        result = await agent.execute("Hello, what can you do?")
        print(result.content)

asyncio.run(main())
```

`get_agent(agent_id)` does not make a network call — it creates a lightweight handle.
The network call happens when you call `execute()`.

## 4. Session management

Every agent call belongs to a *session* — a named conversation thread stored in OpenClaw.
The default session name is `"main"`.

```python
# Two separate sessions for the same agent:
agent_a = client.get_agent("bot", session_name="alice")
agent_b = client.get_agent("bot", session_name="bob")
```

The *session key* sent to the gateway is:

```
agent:{agent_id}:{session_name}
```

## 5. Streaming responses

Use `execute_stream()` to receive events as they arrive instead of waiting for the
full response:

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
        print()  # newline at end

asyncio.run(main())
```

## 6. Configuration options

### Via environment variables (recommended for production)

```bash
export OPENCLAW_GATEWAY_WS_URL=ws://my-server:18789/gateway
export OPENCLAW_API_KEY=your-api-key
```

### Via code

```python
from openclaw_sdk import OpenClawClient

client = await OpenClawClient.connect(
    gateway_ws_url="ws://my-server:18789/gateway",
    api_key="your-api-key",
    timeout=60,
)
```

### Explicit ClientConfig

```python
from openclaw_sdk import OpenClawClient
from openclaw_sdk.core.config import ClientConfig

config = ClientConfig(
    gateway_ws_url="ws://my-server:18789/gateway",
    api_key="your-api-key",
    timeout=60,
)
async with OpenClawClient.connect(**config.model_dump(exclude_none=True)) as client:
    ...
```

## 7. Idempotency

Pass `idempotency_key` to prevent duplicate executions when retrying:

```python
result = await agent.execute(
    "Process order #12345",
    idempotency_key="order-12345-process-v1",
)
```

OpenClaw will return the same result for the same key without re-running the agent.

## 8. Timeouts

Override the global timeout per call via `ExecutionOptions`:

```python
from openclaw_sdk.core.config import ExecutionOptions

result = await agent.execute(
    "Run a long analysis",
    options=ExecutionOptions(timeout_seconds=600),
)
```

## 9. Callbacks

Implement `CallbackHandler` to hook into the execution lifecycle:

```python
from openclaw_sdk.callbacks.handler import CallbackHandler
from openclaw_sdk.core.types import ExecutionResult, StreamEvent

class MyCallback(CallbackHandler):
    async def on_execution_start(self, agent_id: str, query: str) -> None:
        print(f"[START] agent={agent_id}")

    async def on_stream_event(self, agent_id: str, event: StreamEvent) -> None:
        pass  # called for each CONTENT event during streaming

    async def on_execution_end(self, agent_id: str, result: ExecutionResult) -> None:
        print(f"[END]   agent={agent_id}  latency={result.latency_ms}ms")

    async def on_error(self, agent_id: str, error: Exception) -> None:
        print(f"[ERR]   agent={agent_id}  {error}")

# Attach at client level (all agents):
async with OpenClawClient.connect(callbacks=[MyCallback()]) as client:
    await client.get_agent("bot").execute("hello")

# Or attach per-call:
result = await agent.execute("hello", callbacks=[MyCallback()])
```

## 10. Pipeline — multi-agent workflows

Chain agents so each step receives output from the previous one:

```python
from openclaw_sdk.pipeline.pipeline import Pipeline

async with OpenClawClient.connect() as client:
    result = await (
        Pipeline(client)
        .add_step("researcher", "research-bot", "Research: {topic}")
        .add_step("writer", "writer-bot", "Write based on: {researcher}")
        .add_step("editor", "editor-bot", "Edit this article: {writer}")
        .run(topic="electric vehicles in 2025")
    )
    print(result.final_result.content)
```

Template variables in curly braces (`{step_name}`) are filled from:
- Initial variables passed to `run()`
- The `content` of each preceding step

## 11. Structured output

Extract validated Pydantic models from LLM responses:

```python
from pydantic import BaseModel
from openclaw_sdk.output.structured import StructuredOutput

class Sentiment(BaseModel):
    label: str         # "positive", "negative", "neutral"
    confidence: float

async with OpenClawClient.connect() as client:
    agent = client.get_agent("analyst-bot")
    result = await StructuredOutput.execute(
        agent,
        "Analyse the sentiment of: 'I love this product!'",
        Sentiment,
        max_retries=2,
    )
    print(result.label, result.confidence)
```

`StructuredOutput.execute()` appends the JSON schema to the query, then parses the
response — retrying up to `max_retries` times on parse failure.

## 12. FastAPI integration

Install the extra:

```bash
pip install "openclaw-sdk[fastapi]"
```

Mount the routers:

```python
from fastapi import FastAPI
from openclaw_sdk import OpenClawClient
from openclaw_sdk.integrations.fastapi import (
    create_agent_router,
    create_channel_router,
    create_admin_router,
)

app = FastAPI()

@app.on_event("startup")
async def startup():
    app.state.client = await OpenClawClient.connect()

@app.on_event("shutdown")
async def shutdown():
    await app.state.client.close()

# In a dependency or factory:
client = ...
app.include_router(create_agent_router(client))
app.include_router(create_channel_router(client))
app.include_router(create_admin_router(client))
```

## Next Steps

- Browse the [examples/](../examples/) directory for complete, runnable scripts
- See the [README](../README.md) for a full API reference table
- Check `src/openclaw_sdk/` for detailed docstrings on every class and method
