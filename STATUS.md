# OpenClaw SDK — Project Status

> Last updated: 2026-02-21
> Auto-updated by Claude Code after each work session.

---

## Quick Summary

| Metric | Value |
|--------|-------|
| Tests | 669 passing, 12 skipped |
| Coverage | 97%+ |
| mypy | 0 errors (66 files) |
| ruff | 0 issues |
| Python | 3.11+ |
| Version | v0.2.0 |

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
| Tool Policy | DONE | `ToolPolicy` presets (minimal/coding/messaging/full), fluent builders, deny/allow |
| MCP Servers | DONE | `McpServer.stdio()` / `.http()`, per-agent MCP server config |
| Skills Config | DONE | `SkillsConfig` for dynamic discovery via ClawHub, per-skill entries |
| Legacy cleanup | DONE | Removed old ToolConfig classes, ToolType enum, configure_tools() |
| Exports & docs | DONE | All new modules in `__init__.py`, CHANGELOG updated |
| **I/O Alignment** | **DONE** | **All 8 gaps fixed — see below** |

### I/O Alignment with OpenClaw Gateway

| Gap | Status | Notes |
|-----|--------|-------|
| Attachments never sent | DONE | `Attachment.to_gateway()` with base64, size/mime validation |
| Events ignored | DONE | THINKING/TOOL_CALL/TOOL_RESULT/FILE_GENERATED all processed |
| No thinking param | DONE | `ExecutionOptions.thinking` forwarded to chat.send |
| No deliver flag | DONE | `ExecutionOptions.deliver` forwarded to chat.send |
| No timeoutMs | DONE | `timeout_seconds * 1000` forwarded as `timeoutMs` |
| TokenUsage incomplete | DONE | `cache_read`, `cache_write`, `total_tokens` + `from_gateway()` |
| Content not polymorphic | DONE | `ContentBlock` model, `_parse_content()`, `content_blocks` field |
| No aborted state | DONE | `stop_reason="aborted"`, `success=False` |

---

## What's Implemented

### Core
- `OpenClawClient` — factory via `.connect()`, auto-detect gateway, context manager
- `Agent` — `execute()`, `execute_stream()`, `execute_structured()`, `batch()`, callbacks, timeout, idempotency
- `ClientConfig`, `AgentConfig`, `ExecutionOptions` — Pydantic v2 models
- Full exception hierarchy (12 exception classes)
- Enums: `AgentStatus`, `EventType`, `ChannelType`, `GatewayMode`, `MemoryBackend`

### Agent Methods
- `execute(query)` — with cache integration, callbacks, timeout
- `execute_stream(query)` — WebSocket push events
- `execute_structured(query, output_model)` — typed Pydantic model responses
- `batch(queries, max_concurrency=)` — parallel execution
- `wait_for_run(run_id)` — wait for specific run completion
- `get_file(file_path)` — download generated files
- `set_tool_policy(policy)` — runtime tool policy changes
- `deny_tools(*tools)` / `allow_tools(*tools)` — runtime allow/deny
- `add_mcp_server(name, server)` / `remove_mcp_server(name)` — runtime MCP config
- `set_skills(skills)` — runtime skills configuration
- `configure_skill(name, entry)` / `enable_skill()` / `disable_skill()` — per-skill control
- `reset_memory()` / `get_memory_status()` / `get_status()`

### Tool Policy (maps to OpenClaw's native config)
- `ToolPolicy.minimal()` / `.coding()` / `.messaging()` / `.full()` — presets
- `.deny(*tools)` / `.allow_tools(*tools)` — fluent builders (immutable)
- `.with_exec(security=)` / `.with_fs(workspace_only=)` — sub-policy config
- `ExecPolicy`, `FsPolicy`, `ElevatedPolicy`, `WebPolicy` — sub-models

### MCP Servers
- `McpServer.stdio(cmd, args, env)` — stdio transport
- `McpServer.http(url, headers)` — streamable HTTP transport
- Per-agent MCP server configuration

### Skills / Dynamic Discovery
- `SkillsConfig` — controls ClawHub auto-discovery, skill loading, per-skill overrides
- `SkillEntry` — per-skill config (enabled, api_key, env)
- `SkillLoadConfig` — watch mode, extra_dirs for skill filesystem scanning
- `SkillInstallConfig` — package manager preferences
- Runtime: `agent.set_skills()`, `agent.configure_skill()`, `agent.enable/disable_skill()`

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

### Python-Native Features (v0.2)
- `InMemoryCache` — response caching with TTL + LRU eviction
- `Tracer` / `Span` / `TracingCallbackHandler` — observability with JSON export
- `PromptTemplate` — composable templates with `render()`, `partial()`, `+`
- `EvalSuite` — evaluation framework with 4 built-in evaluators
- `Pipeline` — chain agents with `{variable}` template passing
- `StructuredOutput` — parse LLM responses into Pydantic models with retry
- `CallbackHandler` / `LoggingCallbackHandler` / `CompositeCallbackHandler`
- `CostTracker` — per-agent/model cost tracking, CSV/JSON export

### Integration
- FastAPI: `create_agent_router`, `create_channel_router`, `create_admin_router`
- 10 example scripts

### Quality
- `py.typed` marker (PEP 561)
- `LICENSE` (MIT)
- `CHANGELOG.md`, `README.md`, `docs/quickstart.md`, `docs/protocol.md`
- `__openclaw_compat__` = `{"min": "2026.2.0", "max_tested": "2026.2.3-1"}`

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
```
