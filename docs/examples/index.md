# Examples

Complete, runnable example scripts demonstrating every major SDK feature. All examples use `MockGateway` so they work without a live OpenClaw instance.

!!! tip "Running Examples"
    ```bash
    python examples/01_hello_world.py
    ```

---

## 01 — Hello World

Connect to OpenClaw, create an agent, and execute a query.

```python
import asyncio
from openclaw_sdk import OpenClawClient, ClientConfig, AgentConfig, EventType
from openclaw_sdk.core.types import StreamEvent
from openclaw_sdk.gateway.mock import MockGateway

async def main() -> None:
    mock = MockGateway()
    await mock.connect()

    mock.register("chat.send", {"runId": "r1", "status": "started"})
    mock.register("sessions.resolve", {"status": "idle"})
    mock.register("config.get", {"raw": "{}", "exists": True, "path": "/mock"})
    mock.register("config.set", {"ok": True})

    mock.emit_event(StreamEvent(
        event_type=EventType.DONE,
        data={"payload": {"runId": "r1", "content": "Hello from OpenClaw!"}},
    ))

    client = OpenClawClient(config=ClientConfig(), gateway=mock)
    agent = await client.create_agent(AgentConfig(
        agent_id="greeter",
        system_prompt="You are a friendly greeter.",
    ))

    result = await agent.execute("Say hello")
    print(f"Success: {result.success}")
    print(f"Content: {result.content}")
    print(f"Latency: {result.latency_ms} ms")

    await client.close()

asyncio.run(main())
```

**What it demonstrates:** `OpenClawClient`, `MockGateway`, `create_agent()`, `agent.execute()`

---

## 02 — Streaming

Receive incremental content events as the agent generates a response.

```python
import asyncio
from openclaw_sdk import OpenClawClient, ClientConfig, EventType
from openclaw_sdk.core.types import StreamEvent
from openclaw_sdk.gateway.mock import MockGateway

async def main() -> None:
    mock = MockGateway()
    await mock.connect()
    mock.register("chat.send", {"runId": "r1", "status": "started"})

    for chunk in ["Once upon a time ", "in a land far away, ", "an agent learned to stream."]:
        mock.emit_event(StreamEvent(
            event_type=EventType.CONTENT,
            data={"payload": {"runId": "r1", "content": chunk}},
        ))
    mock.emit_event(StreamEvent(
        event_type=EventType.DONE,
        data={"payload": {"runId": "r1"}},
    ))

    client = OpenClawClient(config=ClientConfig(), gateway=mock)
    agent = client.get_agent("storyteller")

    stream = await agent.execute_stream("write a story")
    async for event in stream:
        if event.event_type == EventType.CONTENT:
            chunk = event.data.get("payload", {}).get("content", "")
            print(chunk, end="", flush=True)
        elif event.event_type == EventType.DONE:
            print("\nStream complete.")

    await client.close()

asyncio.run(main())
```

**What it demonstrates:** `execute_stream()`, `StreamEvent`, `EventType.CONTENT`

---

## 03 — FastAPI Backend

Drop-in agent, channel, and admin routers for FastAPI.

```python
from fastapi import FastAPI
from openclaw_sdk import OpenClawClient, ClientConfig
from openclaw_sdk.gateway.mock import MockGateway
from openclaw_sdk.integrations.fastapi import (
    create_agent_router,
    create_channel_router,
    create_admin_router,
)

app = FastAPI(title="OpenClaw SDK Demo")

@app.on_event("startup")
async def startup():
    mock = MockGateway()
    await mock.connect()
    app.state.client = OpenClawClient(config=ClientConfig(), gateway=mock)
    app.include_router(create_agent_router(app.state.client, prefix="/agents"))
    app.include_router(create_channel_router(app.state.client, prefix="/channels"))
    app.include_router(create_admin_router(app.state.client, prefix="/admin"))
```

Run with `uvicorn examples.03_fastapi_backend:app --reload`.

**What it demonstrates:** `create_agent_router()`, `create_channel_router()`, `create_admin_router()`

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/agents/health` | Gateway health check |
| `POST` | `/agents/{id}/execute` | Execute a query |
| `GET` | `/channels/status` | Channel statuses |
| `POST` | `/channels/{ch}/login/start` | Start QR login |
| `GET` | `/admin/schedules` | List cron jobs |
| `GET` | `/admin/skills` | List skills |

---

## 04 — Channel Configuration

Full channel lifecycle: configure, list, QR login, and remove.

**What it demonstrates:** `WhatsAppChannelConfig`, `channels.login()`, `channels.web_login_wait()`, `configure_channel()`, `remove_channel()`

[View source](https://github.com/openclaw/openclaw-sdk/blob/main/examples/04_channel_config.py)

---

## 05 — Tool Policy & MCP Servers

Control agent tools with preset profiles, fluent builders, and MCP server config.

```python
from openclaw_sdk import ToolPolicy
from openclaw_sdk.mcp.server import McpServer

# Preset profiles
minimal = ToolPolicy.minimal()
coding = ToolPolicy.coding()

# Fluent builders (immutable)
safe_coding = (
    ToolPolicy.coding()
    .deny("browser", "canvas")
    .with_fs(workspace_only=True)
    .with_exec(security="deny")
)

# MCP servers
postgres = McpServer.stdio("uvx", ["mcp-server-postgres", "--conn", "postgresql://..."])
github = McpServer.stdio(
    "npx", ["-y", "@modelcontextprotocol/server-github"],
    env={"GITHUB_TOKEN": "ghp_example"},
)
```

**What it demonstrates:** `ToolPolicy` presets and builders, `McpServer.stdio()`, `McpServer.http()`, `agent.set_tool_policy()`, `agent.add_mcp_server()`

---

## 06 — Skills & ClawHub

Manage installed skills and browse the ClawHub marketplace.

**What it demonstrates:** `SkillManager.list_skills()`, `ClawHub.search()`, `ClawHub.get_trending()`, `ClawHub.get_categories()`

[View source](https://github.com/openclaw/openclaw-sdk/blob/main/examples/06_skills_clawhub.py)

---

## 07 — Pipeline

Chain three agents: researcher -> writer -> reviewer.

```python
from openclaw_sdk.pipeline.pipeline import Pipeline

pipeline = (
    Pipeline(client)
    .add_step("research", "researcher", "Research this topic: {topic}")
    .add_step("write", "writer", "Write an article about: {research}")
    .add_step("review", "reviewer", "Review this article: {write}")
)

result = await pipeline.run(topic="AI in 2025")
print(result.final_result.content)
```

**What it demonstrates:** `Pipeline`, `add_step()`, `{variable}` templates, `PipelineResult`

---

## 08 — Structured Output

Parse agent responses into typed Pydantic models.

```python
from pydantic import BaseModel
from openclaw_sdk.output.structured import StructuredOutput

class SalesReport(BaseModel):
    total: float
    units: int
    notes: str

report = await agent.execute_structured(
    "Generate a sales report for Q4",
    output_model=SalesReport,
)
print(f"Revenue: ${report.total:,.2f}")
```

**What it demonstrates:** `execute_structured()`, `StructuredOutput.parse()`, `StructuredOutput.schema_prompt()`

---

## 09 — Callbacks

Custom audit callback + built-in logging via `CompositeCallbackHandler`.

**What it demonstrates:** `CallbackHandler`, `AuditCallbackHandler`, `LoggingCallbackHandler`, `CompositeCallbackHandler`

[View source](https://github.com/openclaw/openclaw-sdk/blob/main/examples/09_callbacks.py)

---

## 10 — Cost Tracking

Track token usage and estimate costs across agents and models.

```python
from openclaw_sdk.tracking.cost import CostTracker

tracker = CostTracker()
# ... run agents ...
summary = tracker.get_summary()
print(f"Total cost: ${summary.total_cost_usd:.4f}")
print(f"By agent: {summary.by_agent}")
await tracker.export_csv("costs.csv")
```

**What it demonstrates:** `CostTracker`, `record()`, `get_summary()`, `export_csv()`
