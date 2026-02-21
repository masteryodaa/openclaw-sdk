# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Fixed — Gateway Protocol (E2E Verified)
- **Auth handshake** — rewrote `ProtocolGateway._handle_challenge()` to use proper `connect` method RPC with Ed25519 device identity signatures (v2 payload format)
- **Request format** — all RPC calls now include `"type": "req"` field (gateway rejects without it)
- **Response parsing** — handle gateway `payload` field (not `result`) and list responses
- **Event handling** — `_execute_impl` now handles real gateway event types (`agent`/`chat` with `state: delta/final`) alongside MockGateway events for backward compatibility
- **idempotencyKey** — now auto-generated (uuid4) for every `chat.send` call (gateway requires it)
- **CronJob model** — `schedule` and `payload` fields accept both `str` and `dict` (gateway returns objects)
- **EventType enum** — added real gateway event types: `AGENT`, `CHAT`, `PRESENCE`, `HEALTH`, `TICK`, `HEARTBEAT`, `CRON`, `SHUTDOWN`

### Added — v0.3.0 Roadmap Features
- **Agent Templates** — 8 pre-built templates (`assistant`, `customer-support`, `data-analyst`, `code-reviewer`, `researcher`, `writer`, `devops`, `mobile-jarvis`); `get_template()`, `list_templates()`, `client.create_agent_from_template()`
- **Conditional Pipelines** — `ConditionalPipeline` with `add_branch()`, `add_parallel()`, `add_fallback()` for branching, concurrent, and fault-tolerant agent workflows
- **Multi-agent Coordination** — `Supervisor` (sequential/parallel/round-robin delegation), `ConsensusGroup` (majority/unanimous/any voting), `AgentRouter` (predicate-based query routing)
- **Guardrails** — `PIIGuardrail` (block/redact/warn), `CostLimitGuardrail`, `ContentFilterGuardrail`, `MaxTokensGuardrail`, `RegexFilterGuardrail`; abstract `Guardrail` base for custom validators
- **Prompt Versioning** — `PromptStore` with save/get/list/diff/rollback/export/import; `PromptVersion` with SHA-256 hashing and tags
- **Multi-tenancy** — `TenantWorkspace` with `TenantConfig` quotas (max agents, cost limits, model restrictions, rate limiting); agent namespacing, usage reports, tenant activation/deactivation
- **Framework Integrations** — Flask (`create_agent_blueprint`, `create_channel_blueprint`), Django (`setup`, `get_urls`), Streamlit (`st_openclaw_chat` widget), Jupyter (`%openclaw` magic commands), Celery (`create_execute_task`, `create_batch_task`)
- **CostCallbackHandler** — callback handler that auto-records execution costs into a `CostTracker`
- **Attachment MIME expansion** — support for images, documents (PDF, CSV, JSON), audio (MP3, OGG, WAV), video (MP4, WebM); configurable max size (25 MB default)

### Added — v0.2.x Features
- **Tool Policy** — `ToolPolicy` with preset profiles (`minimal`, `coding`, `messaging`, `full`) and fluent builders (`.deny()`, `.allow_tools()`, `.with_exec()`, `.with_fs()`); maps directly to OpenClaw's native camelCase tool config
- **MCP Servers** — `McpServer.stdio(cmd, args, env)` and `McpServer.http(url, headers)` for per-agent MCP server configuration
- **Skills Config** — `SkillsConfig` for controlling dynamic tool discovery via ClawHub, skill loading, and per-skill overrides (`SkillEntry`, `SkillLoadConfig`, `SkillInstallConfig`)
- Agent runtime methods: `set_tool_policy()`, `deny_tools()`, `allow_tools()`, `add_mcp_server()`, `remove_mcp_server()`, `set_skills()`, `configure_skill()`, `enable_skill()`, `disable_skill()`
- `AgentConfig.to_openclaw_agent()` — native serialization for `create_agent()`

### Fixed — I/O Alignment with OpenClaw Gateway
- **Attachment model** — `Attachment.to_gateway()` with base64 encoding, configurable size validation, multi-media MIME validation; `Attachment.from_path()` factory with auto-detection
- **TokenUsage** — added `cache_read`, `cache_write`, `total_tokens` fields with camelCase aliases; `TokenUsage.from_gateway()` classmethod; `total` property
- **Event processing** — `_execute_impl` now handles all OpenClaw event types: THINKING, TOOL_CALL, TOOL_RESULT, FILE_GENERATED; populates `thinking`, `tool_calls`, `files`, `token_usage`, `stop_reason` on `ExecutionResult`
- **chat.send params** — forwards `thinking`, `deliver`, `timeoutMs` to gateway; `ExecutionOptions` gains `thinking: bool` and `deliver: bool | None` fields
- **Content polymorphism** — `ContentBlock` model + `_parse_content()` helper handle string-or-array content from gateway; `ExecutionResult.content_blocks` for structured access
- **Aborted state** — `stop_reason="aborted"` + `success=False` when gateway sends aborted state
- **Callbacks** — `on_tool_call`, `on_tool_result`, `on_file_generated` callbacks now actually fired during execution

### Removed
- `ToolConfig`, `DatabaseToolConfig`, `FileToolConfig`, `BrowserToolConfig`, `ShellToolConfig`, `WebSearchToolConfig` — replaced by `ToolPolicy`
- `ToolType` enum — no longer needed with `ToolPolicy` string-based tool names
- `Agent.configure_tools()` — replaced by `Agent.set_tool_policy()`
- `AgentConfig.tools` and `AgentConfig.tool_config` fields — replaced by `AgentConfig.tool_policy`

---

## [0.2.0] — 2026-02-21

### Added
- **Response Cache** — `ResponseCache` ABC + `InMemoryCache` with TTL and LRU eviction; wired into `Agent.execute()` with automatic cache-check-before-gateway and cache-on-success
- **Tracing / Observability** — `Span`, `Tracer`, `TracingCallbackHandler`; hierarchical span tracking with JSON export; auto-creates spans from callback lifecycle events
- **Prompt Templates** — `PromptTemplate` with `render(**vars)`, `partial(**vars)`, composition via `+` operator, and `variables` introspection
- **Batch Execution** — `Agent.batch(queries, max_concurrency=)` for parallel execution with semaphore-based concurrency control
- **Evaluation Framework** — `EvalSuite` with `add_case()`, `evaluate()`, `run(agent)`; built-in evaluators: `ContainsEvaluator`, `ExactMatchEvaluator`, `RegexEvaluator`, `LengthEvaluator`
- **DeviceManager** — `rotate_token(device_id, role)` and `revoke_token(device_id, role)` via verified `device.token.rotate` / `device.token.revoke` gateway methods
- `Agent.wait_for_run(run_id)` — wait for a specific run to complete via `agent.wait` gateway method
- `client.devices` lazy property for device token management

### Fixed
- **ApprovalManager** — rewrote from `NotImplementedError` stub to working `exec.approval.resolve` RPC call (verified against live gateway)

### Protocol Notes (newly verified against OpenClaw 2026.2.3-1)
- `exec.approval.resolve` EXISTS — params: `{id, decision}` where decision is "approve" or "deny"
- `agent.wait` EXISTS — params: `{runId}`
- `device.token.rotate` EXISTS — params: `{deviceId, role}`
- `device.token.revoke` EXISTS — params: `{deviceId, role}`

---

## [0.1.0] — 2026-02-21

### Added
- `OpenClawClient` — main entry point with auto-detection for WebSocket, OpenAI-compat, and local gateway
- `Agent` — `execute()`, `execute_stream()`, `execute_structured()` with full callback support
- `ProtocolGateway` — WebSocket RPC gateway with auth handshake, request/response correlation, reconnect with exponential backoff
- `OpenAICompatGateway` — HTTP adapter for OpenAI-compatible endpoints
- `LocalGateway` — local auto-connecting gateway with socket probe
- `MockGateway` — in-memory gateway for testing
- `Pipeline` — chain multiple agents with `{variable}` template passing
- `StructuredOutput` — parse LLM responses into Pydantic models with retry
- `CallbackHandler` / `LoggingCallbackHandler` / `CompositeCallbackHandler` — execution lifecycle hooks
- `CostTracker` — aggregate token usage and estimate USD costs per agent/model
- `ChannelManager` — `status()`, `logout()`, `web_login_start()`, `web_login_wait()`
- `ScheduleManager` — full cron surface: `list_schedules`, `create_schedule`, `update_schedule`, `delete_schedule`, `run_now`, `get_runs`, `wake`
- `SkillManager` — `list_skills`, `install_skill`, `uninstall_skill`, `enable_skill`, `disable_skill`
- `ClawHub` — `search`, `browse`, `get_details`, `get_categories`, `get_trending`
- `WebhookManager` — stub (CLI-backed)
- `ConfigManager` — full `config.*` surface: `get`, `schema`, `set(raw)`, `patch(raw, baseHash?)`, `apply(raw, baseHash?)`
- `ApprovalManager` — push-event based (raises `NotImplementedError`; use `gateway.subscribe()`)
- `NodeManager` — `system_presence()`, `list()`, `describe()`, `invoke()`
- `OpsManager` — `logs_tail()` (no params), `usage_summary()` (aggregated from sessions)
- `Agent.execute_structured()` — parse LLM responses into typed Pydantic models
- `Agent.get_file()` — download generated files via `files.get`
- `Agent.configure_tools()` — runtime tool configuration via `config.setTools`
- `Agent.reset_memory()` / `Agent.get_memory_status()` / `Agent.get_status()`
- `OpenClawClient.create_agent()` / `list_agents()` / `delete_agent()`
- `OpenClawClient.configure_channel()` / `list_channels()` / `remove_channel()`
- `OpenClawClient.config_mgr` / `approvals` / `nodes` / `ops` properties
- `ChannelManager.login()` — convenience alias for `web_login_start()`
- `ChannelManager.request_pairing_code()` — pairing code flow (WhatsApp)
- 20+ Gateway facade methods for chat, sessions, config, nodes, ops
- `py.typed` marker (PEP 561)
- FastAPI integration: `create_agent_router`, `create_channel_router`, `create_admin_router`
- Config models: `ClientConfig`, `AgentConfig`, `ExecutionOptions`
- Type models: `ExecutionResult`, `StreamEvent`, `ToolCall`, `GeneratedFile`, `TokenUsage`, `AgentSummary`, `HealthStatus`, `Attachment`
- Tool configs: `DatabaseToolConfig`, `FileToolConfig`, `BrowserToolConfig`, `ShellToolConfig`, `WebSearchToolConfig`
- Channel configs: `WhatsAppChannelConfig`, `TelegramChannelConfig`, `DiscordChannelConfig`, `SlackChannelConfig`, `GenericChannelConfig`
- `MemoryConfig` — backend, scope, TTL settings
- Full exception hierarchy: `OpenClawError`, `GatewayError`, `AgentExecutionError`, `TimeoutError`, and more
- Constants: `AgentStatus`, `EventType`, `ChannelType`, `GatewayMode`, `ToolType`, `MemoryBackend`
- 10 example scripts covering all SDK features
- `docs/protocol.md` — protocol freeze, mapping spec, auth/reconnect/channel contracts
- `__openclaw_compat__` version metadata (min: 2026.2.0, max_tested: 2026.2.3-1)
- 409 unit tests, 97% coverage
- `ruff` and `mypy --strict` zero errors

### Protocol Notes (verified against OpenClaw 2026.2.3-1)
- All session methods use `{key}` (not `{sessionKey}`)
- `sessions.preview` uses `{keys: string[]}` array
- `config.set/patch/apply` use `{raw}` (JSON string) with optional `baseHash`
- `logs.tail` accepts no parameters
- `approvals.*` and `usage.*` do not exist on the gateway
- Skills and webhooks are CLI-only, not gateway RPC

[Unreleased]: https://github.com/openclaw/openclaw-sdk/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/openclaw/openclaw-sdk/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/openclaw/openclaw-sdk/releases/tag/v0.1.0
