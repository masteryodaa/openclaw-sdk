# openclaw-sdk

Python SDK for the [OpenClaw](https://github.com/openclaw) autonomous AI agent framework.

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## Overview

OpenClaw is a framework for running autonomous AI agents that communicate via WhatsApp, Telegram, and other channels.  This SDK provides a Pythonic interface to:

- **Execute agents** — send queries and receive results synchronously or as a stream of events
- **Manage channels** — check status, trigger logins, and logout
- **Schedule cron jobs** — create and delete recurring tasks
- **Manage skills** — install, enable, and disable agent capabilities via CLI
- **Monitor costs** — track token usage and USD cost across runs
- **Build pipelines** — chain multiple agents where each step feeds the next
- **Extract structured data** — parse LLM responses into validated Pydantic models
- **Integrate with FastAPI** — drop-in routers for agent, channel, and admin endpoints

---

## Requirements

- Python 3.11+
- A running OpenClaw instance (WebSocket gateway at `ws://127.0.0.1:18789/gateway`)

---

## Installation

```bash
pip install openclaw-sdk
```

With FastAPI integration:

```bash
pip install "openclaw-sdk[fastapi]"
```

---

## Quick Start

```python
import asyncio
from openclaw_sdk import OpenClawClient

async def main():
    async with OpenClawClient.connect() as client:
        agent = client.get_agent("research-bot")
        result = await agent.execute("Summarise the latest AI research papers")
        print(result.content)

asyncio.run(main())
```

`OpenClawClient.connect()` auto-detects the gateway:

1. `OPENCLAW_GATEWAY_WS_URL` environment variable (WebSocket)
2. `OPENCLAW_OPENAI_BASE_URL` environment variable (OpenAI-compatible HTTP)
3. Local socket probe at `127.0.0.1:18789` (auto-connect when OpenClaw is running locally)

---

## Core Concepts

### Gateway

The gateway is the transport layer between the SDK and OpenClaw.  Three implementations are available:

| Gateway | When to use |
|---------|-------------|
| `ProtocolGateway` | WebSocket connection to a remote or local OpenClaw instance |
| `OpenAICompatGateway` | OpenAI-compatible HTTP API (no streaming) |
| `LocalGateway` | Auto-connecting WebSocket for local development |

### Agent

An `Agent` represents a single OpenClaw agent, identified by `agent_id` and an optional `session_name` (default `"main"`).

```python
agent = client.get_agent("research-bot")                  # session: main
agent = client.get_agent("research-bot", session_name="weekly-digest")
print(agent.session_key)  # "agent:research-bot:weekly-digest"
```

### Session Key

The session key scopes conversation history within OpenClaw:

```
agent:{agent_id}:{session_name}
```

### ExecutionResult

`agent.execute()` returns an `ExecutionResult`:

```python
result = await agent.execute("What is the weather in Paris?")
print(result.success)      # True
print(result.content)      # "The current weather in Paris is..."
print(result.latency_ms)   # 1523
```

---

## Usage Examples

### Streaming

```python
async with OpenClawClient.connect() as client:
    agent = client.get_agent("writer-bot")
    stream = await agent.execute_stream("Write a poem about the sea")
    async for event in stream:
        if event.event_type == "content":
            print(event.data["payload"]["content"], end="", flush=True)
```

### Pipeline

```python
from openclaw_sdk.pipeline.pipeline import Pipeline

async with OpenClawClient.connect() as client:
    result = await (
        Pipeline(client)
        .add_step("researcher", "research-bot", "Research: {topic}")
        .add_step("writer", "writer-bot", "Write an article based on: {researcher}")
        .run(topic="quantum computing")
    )
    print(result.final_result.content)
```

### Structured Output

```python
from pydantic import BaseModel
from openclaw_sdk.output.structured import StructuredOutput

class Summary(BaseModel):
    title: str
    key_points: list[str]
    sentiment: str

async with OpenClawClient.connect() as client:
    agent = client.get_agent("analyst-bot")
    summary = await StructuredOutput.execute(agent, "Analyse this article: ...", Summary)
    print(summary.title)
    print(summary.key_points)
```

### Callbacks

```python
from openclaw_sdk.callbacks.handler import CallbackHandler
from openclaw_sdk.core.types import ExecutionResult

class LoggingCallback(CallbackHandler):
    async def on_execution_start(self, agent_id: str, query: str) -> None:
        print(f"[{agent_id}] Starting: {query[:50]}")

    async def on_execution_end(self, agent_id: str, result: ExecutionResult) -> None:
        print(f"[{agent_id}] Done in {result.latency_ms}ms")

async with OpenClawClient.connect(callbacks=[LoggingCallback()]) as client:
    await client.get_agent("bot").execute("hello")
```

### Cost Tracking

```python
from openclaw_sdk.tracking.cost import CostTracker

tracker = CostTracker()
async with OpenClawClient.connect() as client:
    agent = client.get_agent("bot")
    result = await agent.execute("hello")
    tracker.record(result)

print(tracker.summary())
```

### Channel Management

```python
async with OpenClawClient.connect() as client:
    status = await client.channels.status()
    print(status)

    qr = await client.channels.web_login_start("whatsapp")
    print(qr)  # Display QR code

    logged_in = await client.channels.web_login_wait("whatsapp")
    print(logged_in)
```

### Scheduling

```python
from openclaw_sdk.scheduling.manager import ScheduleConfig

async with OpenClawClient.connect() as client:
    config = ScheduleConfig(
        name="daily-report",
        schedule="0 9 * * *",
        session_target="agent:reporter-bot:main",
        payload="Generate the daily summary report",
    )
    job = await client.scheduling.create_schedule(config)
    print(job.id)
```

### FastAPI Integration

```python
from fastapi import FastAPI
from openclaw_sdk.integrations.fastapi import (
    create_agent_router,
    create_channel_router,
    create_admin_router,
)

app = FastAPI()
client = ...  # your OpenClawClient instance

app.include_router(create_agent_router(client, prefix="/agents"))
app.include_router(create_channel_router(client, prefix="/channels"))
app.include_router(create_admin_router(client, prefix="/admin"))
```

Endpoints provided:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/agents/health` | Gateway health check |
| `POST` | `/agents/{agent_id}/execute` | Execute a query |
| `GET` | `/channels/status` | All channel statuses |
| `POST` | `/channels/{channel}/logout` | Logout a channel |
| `POST` | `/channels/{channel}/login/start` | Start QR login |
| `POST` | `/channels/{channel}/login/wait` | Wait for QR scan |
| `GET` | `/admin/schedules` | List cron jobs |
| `DELETE` | `/admin/schedules/{job_id}` | Delete a cron job |
| `GET` | `/admin/skills` | List installed skills |
| `POST` | `/admin/skills/{name}/install` | Install a skill |

---

## Configuration

| Parameter | Env Var | Default | Description |
|-----------|---------|---------|-------------|
| `gateway_ws_url` | `OPENCLAW_GATEWAY_WS_URL` | — | WebSocket URL |
| `openai_base_url` | `OPENCLAW_OPENAI_BASE_URL` | — | OpenAI-compat base URL |
| `api_key` | `OPENCLAW_API_KEY` | — | API key |
| `timeout` | — | `300` | Execution timeout (seconds) |
| `mode` | — | `"auto"` | Gateway selection mode |

```python
from openclaw_sdk import OpenClawClient
from openclaw_sdk.core.config import ClientConfig

config = ClientConfig(
    gateway_ws_url="ws://my-server:18789/gateway",
    api_key="secret",
    timeout=60,
)
async with OpenClawClient.connect(**config.model_dump()) as client:
    ...
```

---

## Compatibility Matrix

| openclaw-sdk | Python | pydantic | websockets |
|-------------|--------|----------|-----------|
| 0.1.x | 3.11, 3.12 | >= 2.0 | >= 12.0 |

---

## Development

```bash
# Clone and install
git clone https://github.com/openclaw/openclaw-sdk
cd openclaw-sdk
pip install -e ".[fastapi]"
pip install pytest pytest-asyncio pytest-cov mypy ruff

# Run tests
pytest tests/ -q

# With coverage
pytest tests/ --cov=src/openclaw_sdk --cov-report=term-missing

# Type check
mypy src/

# Lint
ruff check src/ tests/
```

### Integration Tests

Integration tests require a running OpenClaw instance:

```bash
pytest tests/integration/ -m integration
```

Tests are automatically skipped when OpenClaw is not reachable or not authenticated.

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Write tests for your changes
4. Ensure `pytest`, `mypy`, and `ruff` all pass
5. Open a pull request

---

## License

MIT — see [LICENSE](LICENSE).
