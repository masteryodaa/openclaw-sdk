# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- `Agent.execute_structured()` — convenience method to execute a query and parse the response into a Pydantic model directly on the agent handle
- `Agent.get_file()` — download a generated file by path from the gateway
- `Agent.configure_tools()` — configure tools for an agent session via `config.setTools`
- `Agent.reset_memory()` — clear an agent's conversation memory via `sessions.reset`
- `Agent.get_memory_status()` — get session metadata via `sessions.preview`
- `Agent.get_status()` — get the current `AgentStatus` via `sessions.resolve`
- `OpenClawClient.create_agent()` — create a new agent on the gateway with `AgentConfig`
- `OpenClawClient.list_agents()` — list all agent sessions via `sessions.list`
- `OpenClawClient.delete_agent()` — delete an agent and its sessions via `sessions.delete`
- `OpenClawClient.configure_channel()` — configure a messaging channel via `config.apply`
- `OpenClawClient.list_channels()` — list configured channels via `channels.status`
- `OpenClawClient.remove_channel()` — remove/logout a channel via `channels.logout`
- `OpenClawClient.schedules` property — canonical property name (aliases `scheduling`)
- `OpenClawClient.webhooks` property — `WebhookManager` (stub, CLI-backed)
- `OpenClawClient.config_mgr` property — `ConfigManager` for `config.*` gateway methods
- `OpenClawClient.approvals` property — `ApprovalManager` for execution approvals
- `OpenClawClient.nodes` property — `NodeManager` for node/presence operations
- `OpenClawClient.ops` property — `OpsManager` for logs/update/usage operations
- `ChannelManager.login()` — convenience alias for `web_login_start()`
- `ChannelManager.request_pairing_code()` — request numeric pairing code (WhatsApp)
- `ConfigManager` — full `config.*` surface: `get`, `schema`, `set`, `patch`, `apply`
- `ApprovalManager` — `list_requests()` and `resolve()` for exec approval flow
- `NodeManager` — `system_presence()`, `list()`, `describe()`, `invoke()`
- `OpsManager` — `logs_tail()`, `update_run()`, `usage_summary()`
- Gateway `base.py` facade methods: `chat_history`, `chat_abort`, `chat_inject`, sessions admin (`sessions_list`, `sessions_preview`, `sessions_resolve`, `sessions_patch`, `sessions_reset`, `sessions_delete`, `sessions_compact`), config (`config_get`, `config_schema`, `config_set`, `config_patch`, `config_apply`), approvals, node/presence, ops
- `py.typed` marker (PEP 561) for downstream type-checker support
- `CHANGELOG.md` (this file)

---

## [0.1.0] — 2026-02-18

### Added
- Initial release
- `OpenClawClient` — main entry point with auto-detection for WebSocket, OpenAI-compat, and local gateway
- `Agent` — `execute()` and `execute_stream()` with full callback support
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
- FastAPI integration: `create_agent_router`, `create_channel_router`, `create_admin_router`
- Config models: `ClientConfig`, `AgentConfig`, `ExecutionOptions`
- Type models: `ExecutionResult`, `StreamEvent`, `ToolCall`, `GeneratedFile`, `TokenUsage`, `AgentSummary`, `HealthStatus`, `Attachment`
- Tool configs: `DatabaseToolConfig`, `FileToolConfig`, `BrowserToolConfig`, `ShellToolConfig`, `WebSearchToolConfig`
- Channel configs: `WhatsAppChannelConfig`, `TelegramChannelConfig`, `DiscordChannelConfig`, `SlackChannelConfig`, `GenericChannelConfig`
- `MemoryConfig` — backend, scope, TTL settings
- Full exception hierarchy: `OpenClawError`, `GatewayError`, `AgentExecutionError`, `TimeoutError`, and more
- Constants: `AgentStatus`, `EventType`, `ChannelType`, `GatewayMode`, `ToolType`, `MemoryBackend`
- 10 example scripts covering all SDK features
- 317 unit tests, 96% coverage
- `ruff` and `mypy --strict` zero errors

[Unreleased]: https://github.com/openclaw/openclaw-sdk/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/openclaw/openclaw-sdk/releases/tag/v0.1.0
