# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

*No unreleased changes.*

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

[Unreleased]: https://github.com/openclaw/openclaw-sdk/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/openclaw/openclaw-sdk/releases/tag/v0.1.0
