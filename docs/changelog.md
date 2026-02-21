# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] — 2026-02-21

### Added
- **Built-in MCP Servers** — Two ready-to-use MCP servers: `docs_server` (search/browse SDK docs) and `sdk_server` (interact with live OpenClaw gateway). Install with `pip install "openclaw-sdk[mcp]"`
- **Inkeep Chatbot** — AI-powered documentation search chatbot (requires Inkeep API key)
- **Tool Policy** — `ToolPolicy` with preset profiles (`minimal`, `coding`, `messaging`, `full`) and fluent builders (`.deny()`, `.allow_tools()`, `.with_exec()`, `.with_fs()`); maps directly to OpenClaw's native camelCase tool config
- **MCP Server Config** — `McpServer.stdio(cmd, args, env)` and `McpServer.http(url, headers)` for per-agent MCP server configuration
- **Skills Config** — `SkillsConfig` for controlling dynamic tool discovery via ClawHub, skill loading, and per-skill overrides (`SkillEntry`, `SkillLoadConfig`, `SkillInstallConfig`)
- Agent runtime methods: `set_tool_policy()`, `deny_tools()`, `allow_tools()`, `add_mcp_server()`, `remove_mcp_server()`, `set_skills()`, `configure_skill()`, `enable_skill()`, `disable_skill()`
- `AgentConfig.to_openclaw_agent()` — native serialization for `create_agent()`

### Fixed — I/O Alignment with OpenClaw Gateway
- **Attachment model** — `Attachment.to_gateway()` with base64 encoding, 5 MB size validation, image-only MIME validation; `Attachment.from_path()` factory with auto-detection
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
- `ConfigManager` — full `config.*` surface: `get`, `schema`, `set(raw)`, `patch(raw, baseHash?)`, `apply(raw, baseHash?)`
- `ApprovalManager`, `NodeManager`, `OpsManager`, `DeviceManager`
- FastAPI integration: `create_agent_router`, `create_channel_router`, `create_admin_router`
- Config models: `ClientConfig`, `AgentConfig`, `ExecutionOptions`
- Type models: `ExecutionResult`, `StreamEvent`, `ToolCall`, `GeneratedFile`, `TokenUsage`, `Attachment`, `ContentBlock`
- Full exception hierarchy (14 exception classes)
- `py.typed` marker (PEP 561)
- 669 unit tests, 98% coverage
- `ruff` and `mypy --strict` zero errors
- 10 example scripts
- `docs/quickstart.md`, `docs/protocol.md`

[1.0.0]: https://github.com/openclaw-sdk/openclaw-sdk/compare/v0.2.0...v1.0.0
[0.2.0]: https://github.com/openclaw-sdk/openclaw-sdk/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/openclaw-sdk/openclaw-sdk/releases/tag/v0.1.0
