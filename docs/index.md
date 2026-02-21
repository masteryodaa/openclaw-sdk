---
hide:
  - navigation
  - toc
---

# OpenClaw SDK

<div class="grid cards" markdown>

-   :material-rocket-launch:{ .lg .middle } **Get Started in 5 Minutes**

    ---

    Install the SDK, connect to your OpenClaw instance, and execute your first agent query.

    [:octicons-arrow-right-24: Quickstart](getting-started/quickstart.md)

-   :material-robot:{ .lg .middle } **Agents & Execution**

    ---

    Execute queries, stream responses, extract structured data, and run batch operations.

    [:octicons-arrow-right-24: Agents guide](guides/agents.md)

-   :material-pipe:{ .lg .middle } **Pipelines**

    ---

    Chain multiple agents where each step feeds the next using template variables.

    [:octicons-arrow-right-24: Pipelines guide](guides/pipelines.md)

-   :material-shield-check:{ .lg .middle } **Tool Policy**

    ---

    Control which tools your agents can access with preset profiles and fluent builders.

    [:octicons-arrow-right-24: Tool Policy guide](guides/tool-policy.md)

-   :material-server:{ .lg .middle } **MCP Servers**

    ---

    Connect Model Context Protocol servers to your agents via stdio or HTTP transport.

    [:octicons-arrow-right-24: MCP guide](guides/mcp-servers.md)

-   :material-api:{ .lg .middle } **FastAPI Integration**

    ---

    Drop-in routers for agent execution, channel management, and admin endpoints.

    [:octicons-arrow-right-24: FastAPI guide](guides/fastapi.md)

</div>

---

## What is OpenClaw SDK?

**OpenClaw SDK** is the official Python client for the [OpenClaw](https://github.com/openclaw) autonomous AI agent framework. OpenClaw runs AI agents that communicate via WhatsApp, Telegram, Discord, and other channels. This SDK gives you a Pythonic async interface to:

- **Execute agents** — send queries, receive results synchronously or as streaming events
- **Build pipelines** — chain agents with template-variable passing
- **Extract structured data** — parse LLM responses into validated Pydantic models
- **Manage channels** — connect WhatsApp, Telegram, Discord, Slack
- **Schedule tasks** — create cron jobs for recurring agent operations
- **Track costs** — monitor token usage and USD costs across runs
- **Evaluate quality** — run eval suites with built-in evaluators
- **Observe execution** — hierarchical tracing with span tracking and JSON export

## Quick Example

```python
import asyncio
from openclaw_sdk import OpenClawClient

async def main():
    async with OpenClawClient.connect() as client:
        agent = client.get_agent("research-bot")
        result = await agent.execute("Summarise the latest AI research papers")
        print(result.content)
        print(f"Completed in {result.latency_ms}ms")

asyncio.run(main())
```

## Requirements

| Requirement | Version |
|-------------|---------|
| Python | 3.11+ |
| OpenClaw | 2026.2.0+ |
| pydantic | >= 2.0 |
| websockets | >= 12.0 |

## Installation

```bash
pip install openclaw-sdk
```

With FastAPI integration:

```bash
pip install "openclaw-sdk[fastapi]"
```
