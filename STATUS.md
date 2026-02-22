# OpenClaw SDK — Project Status

> Last updated: 2026-02-22
> Auto-updated by Claude Code after each work session.

---

## Quick Summary

| Metric | Value |
|--------|-------|
| Tests | 1299 passing |
| Coverage | 97%+ |
| mypy | 0 errors (159 files) |
| ruff | 0 issues |
| Python | 3.11+ |
| Version | v2.0.0 |
| Exports | 225 public symbols |

---

## v2.0.0 — Full Feature Release

| Feature | Status | Notes |
|---------|--------|-------|
| Request Deduplication | DONE | SHA-256 fingerprinting, TTL, LRU eviction, asyncio.Lock |
| Semantic Cache | DONE | Cosine similarity matching, agent isolation, configurable threshold |
| retry_async Decorator | DONE | `RetryPolicy.as_decorator()` + `retry_async()` convenience function |
| Plugin System | DONE | `Plugin` ABC, `PluginRegistry` with entry-point discovery, 6 hook types |
| Alerting | DONE | 4 rules (cost/latency/error rate/consecutive), 5 sinks (log/webhook/slack/pagerduty/email), cooldown |
| Audit Logging | DONE | `AuditLogger` with 4 sinks (memory/file/structlog/http), query/filter |
| Billing | DONE | `BillingManager` with pricing tiers, invoice generation, JSON export |
| SMS Channel | DONE | Twilio SMS client, config validation, allowed numbers |
| Data Sources | DONE | ABC + SQLite/Postgres/MySQL/Supabase backends, registry |
| SaaS Connectors | DONE | 10 real connectors: GitHub, Slack, Sheets, Gmail, Notion, Jira, Stripe, HubSpot, Salesforce, Zendesk |
| Autonomous Agents | DONE | `GoalLoop`, `Orchestrator`, `Watchdog`, `Budget` tracking |
| Voice Pipeline | DONE | STT (Whisper/Deepgram) + TTS (OpenAI/ElevenLabs) + VoicePipeline |
| Workflow Engine | DONE | Branching state machine with conditions/approvals/transforms, 3 presets |
| Webhooks Rewrite | DONE | HMAC-SHA256 signing, retry with backoff, delivery tracking |
| Dashboard Backend | DONE | FastAPI app with 13 routers, 25+ endpoints |

---

## v1.0.0 — Full Roadmap Features

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
| MkDocs documentation | DONE | 55+ pages, v2.0 homepage, 34 guides, 21 API refs |
| Command Center | DONE | 19 routers, 17 tabs, 7 new v2.0 modules, all API-tested |
| Built-in MCP Servers | DONE | `docs_server` (search docs), `sdk_server` (gateway operations) |

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
- Full exception hierarchy (29 exception classes incl. retryability metadata)
- `ClientConfig.from_env()` — env var configuration
- Enums: `AgentStatus`, `EventType`, `ChannelType`, `GatewayMode`, `MemoryBackend`

### v2.0 Features
- `RequestDeduplicator` — SHA-256 based request deduplication with TTL
- `SemanticCache` — cosine similarity cache with embedding providers
- `Plugin` / `PluginRegistry` — extensible plugin system with 6 hook points
- `AlertManager` — rule-based alerting with 5 sink types
- `AuditLogger` — audit event logging with query/filter
- `BillingManager` — tenant billing with pricing tiers and invoice generation
- `TwilioSMSClient` — SMS channel via Twilio REST API
- `DataSource` ABC + SQLite/Postgres/MySQL/Supabase implementations
- 10 SaaS connectors with real httpx API calls
- `GoalLoop` / `Orchestrator` / `Watchdog` — autonomous agent execution
- `VoicePipeline` — STT → Agent → TTS audio processing
- `Workflow` — branching state machine with conditions/approvals
- `WebhookManager` — HMAC-signed webhook delivery with retries
- `create_dashboard_app()` — FastAPI dashboard with 13 routers

### Gateways
- `ProtocolGateway` — WebSocket RPC, Ed25519 device auth, reconnect w/ exponential backoff
- `OpenAICompatGateway` — HTTP adapter via httpx
- `LocalGateway` — auto-connect to local OpenClaw
- `MockGateway` — in-memory for testing

### Python-Native Features
- `InMemoryCache` / `SemanticCache` — response caching
- `Tracer` / `Span` / `TracingCallbackHandler` — observability with JSON export
- `PromptTemplate` — composable templates
- `EvalSuite` — evaluation framework with 4 built-in evaluators
- `Pipeline` / `ConditionalPipeline` / `Workflow` — agent chaining
- `StructuredOutput` — parse LLM responses into Pydantic models
- `CostTracker` — per-agent/model cost tracking
- `RetryPolicy` / `retry_async` — retry with exponential backoff
- `CircuitBreaker` / `RateLimiter` — resilience primitives
- `OTelCallbackHandler` — OpenTelemetry integration
- Typed streaming — `execute_stream_typed()` with typed events

### Integration
- FastAPI: `create_agent_router`, `create_channel_router`, `create_admin_router`
- Flask / Django / Streamlit / Jupyter / Celery integrations
- Dashboard: `create_dashboard_app()` — full management API
- 10 example scripts

### Quality
- `py.typed` marker (PEP 561)
- 1299 tests, 97%+ coverage
- E2E verified against live OpenClaw 2026.2.3-1 gateway
- mypy clean (159 files), ruff clean
- MkDocs Material documentation site (55+ pages)
- Command Center with 19 routers, 17 tabs, all API-tested against live gateway

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
