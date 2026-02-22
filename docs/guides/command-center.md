# Command Center

The Command Center is a full-featured web dashboard for managing OpenClaw agents.
Built with FastAPI and backed entirely by the `openclaw-sdk`, it provides a
browser-based UI for chatting with agents, managing sessions, editing configuration,
and monitoring your deployment in real time.

The source lives in `live-examples/command-center/`.

## Quick Start

```bash
cd live-examples/command-center
pip install -r requirements.txt
python main.py
```

The dashboard starts at **http://127.0.0.1:8080**. For hot-reload during development:

```bash
uvicorn main:app --reload --port 8080
```

!!! note "Gateway required"
    The Command Center connects to a running OpenClaw instance at
    `ws://127.0.0.1:18789/gateway`. If the gateway is unavailable at startup the
    app will warn and retry on the first request.

## Tabs

The UI is organized into 17 tabs covering every aspect of agent management:

| Tab | Purpose |
|-----|---------|
| **Chat** | Send messages with streaming responses, view an event timeline (tool calls, thinking, generated files), upload file attachments with inline preview |
| **Sessions** | List, preview, reset, compact, and delete conversation sessions |
| **Config** | View and edit the runtime configuration (full replace or compare-and-swap patch) |
| **Agents** | Create, delete, and inspect agents; manage tool allow/deny lists and MCP servers |
| **Models** | Browse available models and per-agent model assignments |
| **Schedules** | List and delete cron-scheduled jobs |
| **Channels** | View channel statuses |
| **Templates** | List and inspect agent templates |
| **Pipelines** | Manage chained agent pipelines |
| **Workflows** | Run preset multi-agent workflows (review, research, support) |
| **Autonomous** | Configure and monitor autonomous agent runs |
| **Connectors** | Browse available SaaS connector classes |
| **Webhooks** | Register, list, and test-fire webhooks |
| **Observe** | Cost tracking (summary, daily breakdown, per-entry log), tracing, and prompt versioning with diff |
| **Guardrails** | View and manage input/output guardrail rules |
| **Billing** | Query tenant usage and generate invoices |
| **Audit** | Search the audit log with event-type and agent-id filters |

## Chat Features

The Chat tab is the primary interaction surface:

- **Streaming responses** -- messages are delivered via Server-Sent Events so content, thinking, tool calls, and tool results appear incrementally.
- **Event timeline** -- every tool call, tool result, thinking block, and generated file is displayed in order alongside the final response.
- **File attachments** -- upload files from the browser (base64-encoded, up to the gateway's ~380 KB frame limit) and see inline previews for images.
- **Session management** -- pick an agent and session name, reset memory, or abort a running query without leaving the tab.

## Observe Tab

The Observe tab combines three observability features in one view:

- **Cost tracking** -- total spend, per-agent and per-model breakdowns, daily charts, and a scrollable entry log.
- **Tracing** -- recorded spans exported as JSON for debugging latency and execution flow.
- **Prompt versioning** -- save, list, rollback, and diff prompt versions directly from the browser.

## Architecture

The Command Center is a standard FastAPI application. On startup it creates a single
`OpenClawClient` connection that is shared across all request handlers. Every tab
maps to one or more route modules under `app/`, each calling the SDK's public API:

```
Browser  -->  FastAPI (routes_*.py)  -->  OpenClawClient  -->  OpenClaw Gateway
```

!!! tip "Extending the dashboard"
    Because it is a regular FastAPI app, you can add custom routes, middleware,
    or authentication the same way you would with any FastAPI project. See the
    [Dashboard guide](dashboard.md) for patterns like mounting under a prefix or
    adding token-based auth.
