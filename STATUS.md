# OpenClaw SDK — Project Status

> Last updated: 2026-02-21
> Auto-updated by Claude Code after each work session.

---

## Quick Summary

| Metric | Value |
|--------|-------|
| Tests | 806 passing, 12 skipped |
| Coverage | 97%+ |
| mypy | 0 errors (84 files) |
| ruff | 0 issues |
| Python | 3.11+ |
| Version | v0.3.0-dev |
| Exports | 100+ public symbols |

---

## v0.3.0 — Full Roadmap Features

| Feature | Status | Notes |
|---------|--------|-------|
| Agent Templates | DONE | 8 pre-built templates, `get_template()`, `list_templates()`, `create_agent_from_template()` |
| Conditional Pipelines | DONE | `ConditionalPipeline` with branch/parallel/fallback steps |
| Multi-agent Coordination | DONE | `Supervisor`, `ConsensusGroup`, `AgentRouter` |
| Guardrails | DONE | PII, cost limit, content filter, max tokens, regex + custom base class |
| Prompt Versioning | DONE | `PromptStore` with save/get/diff/rollback/export/import |
| Multi-tenancy | DONE | `TenantWorkspace` with quotas, namespacing, usage reports |
| CostCallbackHandler | DONE | Auto-records costs into CostTracker |
| Attachment MIME expansion | DONE | Images, documents, audio, video; 25 MB configurable limit |
| Flask integration | DONE | `create_agent_blueprint`, `create_channel_blueprint` |
| Django integration | DONE | `setup()`, `get_urls()` |
| Streamlit widget | DONE | `st_openclaw_chat()` with thinking + token display |
| Jupyter magics | DONE | `%openclaw_connect`, `%openclaw`, `%openclaw_agent` |
| Celery integration | DONE | `create_execute_task`, `create_batch_task` |
| MkDocs documentation | DONE | 30+ pages, marketing homepage, custom CSS theme |

---

## v0.2.0 — LangChain-Parity Features

| Feature | Status | Notes |
|---------|--------|-------|
| Response Cache | DONE | `InMemoryCache` with TTL + LRU, wired into `Agent.execute()` |
| Tracing / Observability | DONE | `Span`, `Tracer`, `TracingCallbackHandler` with JSON export |
| Prompt Templates | DONE | `PromptTemplate` with `render()`, `partial()`, `+` composition |
| Batch Execution | DONE | `Agent.batch(queries, max_concurrency=)` with semaphore |
| Evaluation Framework | DONE | `EvalSuite` + 4 evaluators: Contains, ExactMatch, Regex, Length |
| DeviceManager | DONE | `rotate_token()`, `revoke_token()` via verified gateway RPC |
| ApprovalManager fix | DONE | Rewrote to use `exec.approval.resolve` (verified RPC) |
| Agent.wait_for_run() | DONE | Via `agent.wait` gateway method |
| Tool Policy | DONE | `ToolPolicy` presets (minimal/coding/messaging/full), fluent builders |
| MCP Servers | DONE | `McpServer.stdio()` / `.http()`, per-agent MCP server config |
| Skills Config | DONE | `SkillsConfig` for dynamic discovery, per-skill entries |
| **I/O Alignment** | **DONE** | **All 8 gaps fixed** |

---

## What's Implemented

### Core
- `OpenClawClient` — factory via `.connect()`, auto-detect gateway, context manager
- `Agent` — `execute()`, `execute_stream()`, `execute_structured()`, `batch()`, callbacks, timeout, idempotency
- `ClientConfig`, `AgentConfig`, `ExecutionOptions` — Pydantic v2 models
- Full exception hierarchy (12 exception classes)
- Enums: `AgentStatus`, `EventType`, `ChannelType`, `GatewayMode`, `MemoryBackend`

### v0.3 Features
- `ConditionalPipeline` — branching, parallel, fallback agent workflows
- `Supervisor` / `ConsensusGroup` / `AgentRouter` — multi-agent coordination
- `PIIGuardrail` / `CostLimitGuardrail` / `ContentFilterGuardrail` / `MaxTokensGuardrail` / `RegexFilterGuardrail`
- `PromptStore` / `PromptVersion` — versioned prompt management
- `TenantWorkspace` / `TenantConfig` / `Tenant` — multi-tenant isolation
- `get_template()` / `list_templates()` — pre-built agent templates
- `CostCallbackHandler` — auto cost tracking callback
- Framework integrations: Flask, Django, Streamlit, Jupyter, Celery

### Client Properties
- `client.channels` → ChannelManager
- `client.schedules` → ScheduleManager
- `client.skills` → SkillManager
- `client.clawhub` → ClawHub
- `client.webhooks` → WebhookManager
- `client.config_mgr` → ConfigManager
- `client.approvals` → ApprovalManager
- `client.nodes` → NodeManager
- `client.ops` → OpsManager
- `client.devices` → DeviceManager

### Gateways
- `ProtocolGateway` — WebSocket RPC, auth handshake, reconnect w/ exponential backoff
- `OpenAICompatGateway` — HTTP adapter via httpx
- `LocalGateway` — auto-connect to local OpenClaw
- `MockGateway` — in-memory for testing

### Python-Native Features
- `InMemoryCache` — response caching with TTL + LRU eviction
- `Tracer` / `Span` / `TracingCallbackHandler` — observability with JSON export
- `PromptTemplate` — composable templates with `render()`, `partial()`, `+`
- `EvalSuite` — evaluation framework with 4 built-in evaluators
- `Pipeline` — chain agents with `{variable}` template passing
- `StructuredOutput` — parse LLM responses into Pydantic models with retry
- `CostTracker` — per-agent/model cost tracking, CSV/JSON export

### Integration
- FastAPI: `create_agent_router`, `create_channel_router`, `create_admin_router`
- Flask: `create_agent_blueprint`, `create_channel_blueprint`
- Django: `setup()`, `get_urls()`
- Streamlit: `st_openclaw_chat()`
- Jupyter: `%openclaw` magics
- Celery: `create_execute_task`, `create_batch_task`
- 10 example scripts

### Quality
- `py.typed` marker (PEP 561)
- 806 tests, 97%+ coverage
- mypy clean (84 files), ruff clean
- MkDocs Material documentation site (30+ pages)

---

## How to Run

```bash
# Tests
python -m pytest tests/ -q

# Type check
python -m mypy src/ --ignore-missing-imports

# Lint
python -m ruff check src/ tests/

# Coverage
python -m pytest tests/ --cov=openclaw_sdk --cov-report=term-missing

# Docs
python -m mkdocs serve
```
