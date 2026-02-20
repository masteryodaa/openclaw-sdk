# OpenClaw Gateway Protocol Reference

**SDK Version**: 0.1.0
**Tested Against**: OpenClaw 2026.2.3-1
**Last Verified**: 2026-02-21

---

## 1. Protocol Freeze — Method Names & Payloads

All method names, parameters, and response shapes below are pinned for OpenClaw
version range **2026.2.0 – 2026.2.3-1**. The SDK will warn on startup if the
connected gateway falls outside this range.

### 1.1 Chat Methods

| Method | Parameters | Response |
|--------|-----------|----------|
| `chat.send` | `{sessionKey, message, idempotencyKey?}` | `{runId, status: "started"}` |
| `chat.history` | `{sessionKey, limit?}` | `{sessionKey, sessionId, messages: [...]}` |
| `chat.abort` | `{sessionKey}` | `{ok: true}` |
| `chat.inject` | `{sessionKey, message}` | `{ok: true}` |

### 1.2 Session Methods

| Method | Parameters | Response |
|--------|-----------|----------|
| `sessions.list` | `{}` | `{count, defaults, sessions: [...]}` |
| `sessions.preview` | `{keys: string[]}` | Preview data for given session keys |
| `sessions.resolve` | `{key}` | Session state for the given key |
| `sessions.patch` | `{key, ...patch}` | `{ok: true}` |
| `sessions.reset` | `{key}` | `{ok: true}` |
| `sessions.delete` | `{key}` | `{ok, key, deleted, archived}` |
| `sessions.compact` | `{key}` | `{ok, key, compacted, kept}` |

**Session key format**: `"agent:{agent_id}:{session_name}"` (e.g., `"agent:main:main"`)

**Session object shape**:
```json
{
  "key": "agent:main:main",
  "kind": "direct",
  "chatType": "direct",
  "sessionId": "dfe9835c-...",
  "updatedAt": 1771360111367,
  "inputTokens": 3172,
  "outputTokens": 190,
  "totalTokens": 28746,
  "modelProvider": "anthropic",
  "model": "claude-opus-4-5",
  "contextTokens": 200000
}
```

### 1.3 Config Methods

| Method | Parameters | Response |
|--------|-----------|----------|
| `config.get` | `{}` | `{path, exists, raw, parsed, hash}` |
| `config.schema` | `{}` | `{schema: {$schema, type, properties, ...}}` |
| `config.set` | `{raw}` | `{ok, path, config}` |
| `config.patch` | `{raw, baseHash?}` | `{ok, path, config}` |
| `config.apply` | `{raw, baseHash?}` | `{ok, path, config}` |

**Compare-and-swap**: `config.patch` and `config.apply` support `baseHash` (SHA-256)
for optimistic concurrency. Obtain the hash from `config.get` response.

### 1.4 Channel Methods

| Method | Parameters | Response |
|--------|-----------|----------|
| `channels.status` | `{}` | `{channelOrder, channelLabels, channels: {...}}` |
| `channels.logout` | `{channel}` | `{ok: true}` |
| `web.login.start` | `{channel}` | `{qrDataUrl: "data:image/png;base64,..."}` |
| `web.login.wait` | `{channel, timeoutMs?}` | `{linked, phone?, ...}` |

### 1.5 Cron/Schedule Methods

| Method | Parameters | Response |
|--------|-----------|----------|
| `cron.list` | `{}` | `{jobs: [...]}` |
| `cron.status` | `{}` | `{enabled, storePath, ...}` |
| `cron.add` | `{name, schedule, sessionTarget, payload}` | Job object |
| `cron.update` | `{id, patch}` | `{ok: true}` |
| `cron.remove` | `{id}` | `{ok: true}` |
| `cron.run` | `{id}` | `{ok: true}` |
| `cron.runs` | `{id?, limit?}` | Run history |
| `wake` | `{mode?, text?}` | `{ok: true}` |

### 1.6 Node/Presence Methods

| Method | Parameters | Response |
|--------|-----------|----------|
| `system-presence` | `{}` | Presence data |
| `node.list` | `{}` | `{ts, nodes: [...]}` |
| `node.describe` | `{nodeId}` | Node details |
| `node.invoke` | `{nodeId, action, payload?}` | Action result |

### 1.7 Ops Methods

| Method | Parameters | Response |
|--------|-----------|----------|
| `logs.tail` | `{}` (no params accepted) | `{file, cursor, ...}` |

### 1.8 Methods That Do NOT Exist on Gateway

| Category | Notes |
|----------|-------|
| `approvals.*` | Push-event based only (`approval.requested` via subscribe) |
| `usage.*` | Usage data embedded in session metadata (`inputTokens`, `outputTokens`, `totalTokens`) |
| `update.run` | Not verified; removed from SDK |
| `skills.*` | CLI-only (`openclaw skills list/info/check`) |
| `webhooks.*` | CLI-only integrations, no generic API |
| `plugins.*` | Configured in `openclaw.json`, not via gateway RPC |
| `channels.list` | Use `channels.status` instead |

---

## 2. Mapping Spec — Protocol Payloads to SDK Models

Deterministic mapping from gateway protocol payloads to SDK Pydantic models:

### 2.1 ExecutionResult

| Protocol Field | SDK Field | Type | Notes |
|---------------|-----------|------|-------|
| `chat.send` → subscribe `DONE` event | `ExecutionResult` | model | Assembled from events |
| `payload.content` | `.content` | `str` | Final LLM response text |
| `payload.runId` | (internal) | `str` | Used for event correlation |
| Event `TOOL_CALL` payloads | `.tool_calls` | `list[ToolCall]` | Accumulated during stream |
| Event `FILE_GENERATED` payloads | `.files` | `list[GeneratedFile]` | Accumulated during stream |
| Event `THINKING` payloads | `.thinking` | `str \| None` | Concatenated thinking text |
| Session metadata `inputTokens` | `.token_usage.input` | `int` | From session object |
| Session metadata `outputTokens` | `.token_usage.output` | `int` | From session object |
| Computed (start → done) | `.latency_ms` | `int` | Wall-clock execution time |
| Always `True` unless error | `.success` | `bool` | `False` on exception |

### 2.2 StreamEvent

| Protocol Field | SDK Field | Type |
|---------------|-----------|------|
| `event` field or inferred | `.event_type` | `EventType` enum |
| Full event envelope | `.data` | `dict` |

### 2.3 ToolCall

| Protocol Field | SDK Field | Type |
|---------------|-----------|------|
| `payload.tool` | `.tool` | `str` |
| `payload.input` | `.input` | `str` |
| `payload.output` | `.output` | `str \| None` |
| `payload.durationMs` | `.duration_ms` | `int \| None` |

### 2.4 GeneratedFile

| Protocol Field | SDK Field | Type |
|---------------|-----------|------|
| `payload.name` | `.name` | `str` |
| `payload.path` | `.path` | `str` |
| `payload.sizeBytes` | `.size_bytes` | `int` |
| `payload.mimeType` | `.mime_type` | `str` |

### 2.5 AgentSummary

| Protocol Field | SDK Field | Type | Notes |
|---------------|-----------|------|-------|
| `session.key` | `.agent_id` | `str` | Extracted from key: `"agent:{id}:main"` |
| Not in protocol | `.name` | `str \| None` | From config, not session |
| Inferred from session state | `.status` | `AgentStatus` | Mapped from session presence |

### 2.6 Error Mapping

| Gateway Error | SDK Exception | Condition |
|--------------|---------------|-----------|
| `error.code` present | `GatewayError` | Any gateway error response |
| Connection refused | `ConnectionError` | Cannot reach gateway |
| Auth failure | `GatewayError(code="AUTH_FAILED")` | Invalid/missing token |
| `invalid ... params` | `ConfigurationError` | Bad parameters |
| Agent not in sessions | `AgentNotFoundError` | Unknown agent_id |
| Timeout waiting for DONE | `TimeoutError` | Execution exceeded timeout |
| Stream interrupted | `StreamError` | WebSocket disconnect during stream |

---

## 3. Handshake & Auth Contract

### 3.1 Connection Flow

```
Client                              Gateway
  |                                    |
  |--- WebSocket connect ------------->|
  |                                    |
  |<-- connect.challenge --------------|
  |    {nonce, ts}                     |
  |                                    |
  |--- auth response ----------------->|
  |    {type: "auth", token, nonce}    |
  |                                    |
  |<-- auth.success -------------------|
  |    (or auth.failure)               |
  |                                    |
  |=== Authenticated session ==========>|
```

### 3.2 Auth Token Source

Priority order:
1. `OPENCLAW_GATEWAY_TOKEN` environment variable
2. `api_key` parameter in `ClientConfig`
3. `~/.openclaw/openclaw.json` → `gateway.auth.token`

### 3.3 Auth Mode

The gateway supports `token` auth mode (configured in `gateway.auth.mode`).
The token is a static secret — no OAuth, JWT rotation, or scopes in v0.1.

### 3.4 Failure Modes

| Failure | Gateway Behavior | SDK Response |
|---------|-----------------|--------------|
| Missing token | Connection rejected | `GatewayError("AUTH_FAILED")` |
| Invalid token | Connection rejected | `GatewayError("AUTH_FAILED")` |
| Expired nonce | Connection rejected | Reconnect with new handshake |
| Network timeout | No response | Retry with backoff (see Section 4) |

---

## 4. Reconnect & Resume Contract

### 4.1 Retry Strategy

| Parameter | Value | Notes |
|-----------|-------|-------|
| Initial delay | 1 second | After first disconnect |
| Backoff multiplier | 2x | Exponential |
| Max delay | 30 seconds | Cap on backoff |
| Max retries | `ClientConfig.max_retries` (default: 3) | Configurable |
| Jitter | +/- 10% | Prevents thundering herd |

### 4.2 In-Flight Request Handling

- Requests with `idempotencyKey` are safe to retry — gateway deduplicates
- Requests without idempotency key may be re-sent; gateway treats as new request
- `chat.send` supports `idempotencyKey` parameter for exactly-once semantics
- Pending subscribe iterators are re-established after reconnect

### 4.3 Session Resume

- Sessions are server-side persistent (keyed by `sessionKey`)
- Reconnect does NOT lose session state
- In-progress `chat.send` runs continue server-side even if SDK disconnects
- SDK re-subscribes to events after reconnect to receive remaining events

### 4.4 Duplicate Suppression

- SDK tracks `runId` of in-flight executions
- If a DONE event arrives for an already-completed `runId`, it is dropped
- `idempotencyKey` ensures the gateway does not start duplicate runs

---

## 5. Channel Onboarding Contract

### 5.1 State Machine (per channel)

```
                 ┌──────────────┐
                 │ UNCONFIGURED │
                 └──────┬───────┘
                        │ configure_channel()
                        ▼
                 ┌──────────────┐
                 │  CONFIGURED  │ (configured=true, linked=false)
                 └──────┬───────┘
                        │ web_login_start() or login()
                        ▼
                 ┌──────────────┐
                 │ PAIRING      │ (QR code displayed / pairing code sent)
                 └──────┬───────┘
                        │ web_login_wait() → {linked: true}
                        ▼
                 ┌──────────────┐
                 │   LINKED     │ (configured=true, linked=true, running=true)
                 └──────┬───────┘
                        │ channels.logout()
                        ▼
                 ┌──────────────┐
                 │ DISCONNECTED │ (configured=true, linked=false)
                 └──────────────┘
```

### 5.2 Supported Onboarding Flows

| Channel | Flow | SDK Methods |
|---------|------|------------|
| WhatsApp | QR code scan | `web_login_start()` → render QR → `web_login_wait()` |
| WhatsApp | Pairing code | `request_pairing_code(channel, phone)` |
| Telegram | Bot token | Configure via `config.set` (bot token in config) |
| Discord | Bot token | Configure via `config.set` (bot token in config) |
| Slack | OAuth | Configure via `config.set` (app credentials in config) |

### 5.3 Error Transitions

| Error | From State | To State | SDK Behavior |
|-------|-----------|----------|--------------|
| QR timeout | PAIRING | CONFIGURED | `ChannelError("QR scan timeout")` |
| Invalid phone | CONFIGURED | CONFIGURED | `ChannelError("Invalid phone number")` |
| Auth revoked | LINKED | DISCONNECTED | Push event, `channels.status` reflects |
| Network loss | LINKED | DISCONNECTED | Auto-reconnect (channel-level) |

---

## 6. Version Matrix

### 6.1 Tested Versions

| SDK Version | OpenClaw Version | Status | Notes |
|-------------|-----------------|--------|-------|
| 0.1.0 | 2026.2.3-1 | Fully tested | Primary development target |
| 0.1.0 | 2026.2.0+ | Expected compatible | Same major protocol version |
| 0.1.0 | < 2026.2.0 | Untested | May work, no guarantees |
| 0.1.0 | 2026.3.x | Untested | May introduce breaking changes |

### 6.2 Known Limitations

| Feature | Limitation | Workaround |
|---------|-----------|-----------|
| Approvals | No RPC methods; push-event only | Use `gateway.subscribe()` for `approval.requested` events |
| Usage stats | No `usage.*` endpoint | Aggregate from `sessions.list` metadata |
| Skills | No gateway RPC | SDK uses subprocess CLI (`openclaw skills`) |
| Webhooks | No gateway RPC | SDK raises `NotImplementedError` (CLI-only) |
| Plugins | No gateway RPC | Configure directly in `~/.openclaw/openclaw.json` |
| `update.run` | Not verified on gateway | Removed from SDK |

### 6.3 SDK Metadata

```python
import openclaw_sdk

openclaw_sdk.__version__          # "0.1.0"
openclaw_sdk.__openclaw_compat__  # {"min": "2026.2.0", "max_tested": "2026.2.3-1"}
```
