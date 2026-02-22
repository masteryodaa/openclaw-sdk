# OpenClaw Command Center

Full-stack web dashboard for managing OpenClaw agents, powered by `openclaw-sdk`.
Covers the entire SDK surface: chat, sessions, config, channels, schedules, and system ops.

## Run

```bash
cd live-examples/command-center
pip install openclaw-sdk[fastapi] uvicorn sse-starlette
python main.py
```

Open http://127.0.0.1:8080

## Features

### Chat
- Real-time streaming via SSE with token-by-token output
- Agent selection dropdown with dynamic agent list
- Thinking mode toggle (extended reasoning)
- Tool call / result display
- File generation display with download links
- Abort running chat, inject messages
- LLM error detection (`error_message` on 429/auth failures)

### Sessions
- List all sessions with model, token counts, last updated
- Reset memory, compact history, delete sessions
- Session preview (message history)

### Models & Providers
- Switch LLM provider (Anthropic, OpenAI, Gemini, Ollama) per agent
- Model selection with known models + custom model support
- API key management per agent
- Runtime model switching without restart

### Pipelines & Workflows
- Linear multi-step agent pipelines with template variables
- Supervisor pattern (sequential, parallel, round-robin)
- Keyword-based agent routing
- Batch execution (parallel queries against single agent)
- Agent templates (pre-built configs for common use cases)

### Guardrails & Eval
- Safety checks: keyword filter, PII detection, content length, regex filter
- Input and output validation
- Agent evaluation: run test cases with expected outputs

### Observability
- Cost tracking: total queries, costs, tokens, latency
- Per-agent cost breakdown
- Recent cost entries timeline
- Prompt versioning: save, list, rollback, diff prompts

### Config
- View and edit full OpenClaw configuration (JSON editor)
- Hash-based compare-and-swap saves (prevents overwrites)
- Config schema viewer

### Channels
- Per-channel status cards with login state badges
- Login/logout, pairing code generation
- Support for WhatsApp, Telegram, Discord, Slack, etc.

### Schedules
- Cron job table with schedule, agent, status
- Create, update, delete schedules
- Run now (trigger immediately), run history

### System
- Gateway health monitoring
- Node/presence information
- Live log tailing
- Approval resolution (approve/deny pending tool calls)
- Device token management (rotate/revoke)

## API Endpoints (65+ total)

| Module | Endpoints |
|--------|-----------|
| Health | `GET /api/health` |
| Agents | `GET/POST/DELETE /api/agents`, reset, preview, status, wait, abort, inject, tools, MCP, files, details, history |
| Chat | `POST /api/chat`, `GET /api/chat/stream` |
| Models | `GET /api/models/providers`, `GET /api/models/all`, `GET /api/models/agent/{id}`, `POST /api/models/set` |
| Config | `GET/PUT/PATCH /api/config`, `GET /api/config/schema` |
| Sessions | `GET/DELETE /api/sessions`, preview, resolve, reset, compact, patch |
| Pipelines | `POST /api/pipelines/run`, supervisor, router, batch, `GET/POST /api/pipelines/templates` |
| Guardrails | `GET /api/guardrails/available`, `POST /api/guardrails/check/input`, check/output, eval |
| Observe | `GET /api/observe/costs`, costs/daily, costs/entries, costs/pricing, `DELETE /api/observe/costs`, `GET /api/observe/traces`, prompts CRUD |
| Channels | `GET /api/channels/status`, login, login/wait, pairing-code, logout |
| Schedules | `GET/POST/PATCH/DELETE /api/schedules`, run, runs |
| Ops | `GET /api/ops/logs`, nodes, devices, `POST /api/ops/approvals/resolve`, device token rotate/revoke |

## Structure

```
command-center/
  main.py                  # FastAPI entry point (v3.0)
  app/
    __init__.py
    gateway.py             # Shared OpenClaw client singleton
    routes_health.py       # /api/health
    routes_agents.py       # /api/agents — CRUD, sessions, tools, MCP, files, introspection
    routes_chat.py         # /api/chat — blocking + SSE streaming
    routes_models.py       # /api/models — provider/model switching
    routes_config.py       # /api/config — get, set, patch, schema
    routes_sessions.py     # /api/sessions — list, preview, manage
    routes_pipelines.py    # /api/pipelines — workflows, batch, templates, coordination
    routes_guardrails.py   # /api/guardrails — safety checks, evaluation
    routes_observe.py      # /api/observe — costs, traces, prompt versioning
    routes_channels.py     # /api/channels — status, login/logout, pairing
    routes_schedules.py    # /api/schedules — CRUD, run now, history
    routes_ops.py          # /api/ops — logs, nodes, devices, approvals
  static/
    index.html             # 10-tab single-page dashboard
```

## Requirements

- Python 3.11+
- OpenClaw running locally (`openclaw start`)
- `openclaw-sdk[fastapi]`, `uvicorn`, `sse-starlette`
