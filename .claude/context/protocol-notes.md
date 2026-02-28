# OpenClaw Gateway Protocol Notes

**Status**: UPDATED — probed live from OpenClaw dev build (post-2026.2.26)
**Updated**: 2026-02-28
**Gateway URL**: `ws://127.0.0.1:18789`
**Methods**: 93 verified | **Events**: 19 verified | **Protocol version**: 3

---

## Auth Token

The gateway auth token lives in `~/.openclaw/openclaw.json` at `gateway.auth.token`.
SDK should read it from env var `OPENCLAW_GATEWAY_TOKEN` or config file.

---

## Connection & Auth Flow (VERIFIED 2026-02-21)

On WebSocket connect, the gateway pushes a challenge:
```json
{"type":"event","event":"connect.challenge","payload":{"nonce":"ad8a2bb0-...","ts":1771605731312}}
```

SDK responds with a `connect` method RPC (NOT a simple auth message):
```json
{
  "type": "req", "id": "req_1", "method": "connect",
  "params": {
    "minProtocol": 3, "maxProtocol": 3,
    "client": {"id": "cli", "version": "0.3.0", "platform": "windows", "mode": "cli"},
    "role": "operator",
    "scopes": ["operator.admin", "operator.approvals", "operator.pairing"],
    "caps": [], "commands": [], "permissions": {},
    "auth": {"token": "<operator_device_token>"},
    "locale": "en-US", "userAgent": "openclaw-sdk/0.3.0",
    "device": {
      "id": "<deviceId>",
      "publicKey": "<base64url_raw_ed25519_pubkey>",
      "signature": "<base64url_ed25519_signature>",
      "signedAt": 1771664000000,
      "nonce": "<challenge_nonce>"
    }
  }
}
```

### Ed25519 Signing Payload (v2)
Pipe-delimited string, UTF-8 encoded:
```
v2|deviceId|cli|cli|role|scopes_comma_separated|signedAtMs|token|nonce
```

### Device Identity Files
- `~/.openclaw/identity/device.json` — deviceId, Ed25519 public/private key PEM
- `~/.openclaw/identity/device-auth.json` — operator token, role, scopes

### Critical Constants
- `client.id` MUST be `"cli"` (schema-validated constant)
- `client.mode` MUST be `"cli"` (schema-validated constant)

### Connect Response
```json
{"type":"res","id":"req_1","ok":true,"payload":{"type":"hello-ok","protocol":3,"server":{...},"features":{...}}}
```

---

## Request/Response Envelope (VERIFIED 2026-02-21)

```json
// Request (SDK -> Gateway) — MUST include "type": "req"
{"type": "req", "id": "req_1", "method": "sessions.list", "params": {}}

// Success response — uses "payload" NOT "result"
{"type": "res", "id": "req_1", "ok": true, "payload": {...}}

// Error response
{"id": "req_1", "error": {"code": ..., "message": "invalid sessions.list params: ..."}}

// Push event (Gateway -> SDK, no id)
{"type": "event", "event": "connect.challenge", "payload": {"nonce": "...", "ts": ...}}
```

**CRITICAL**: All RPC requests MUST include `"type": "req"` — without it the gateway
returns `"invalid request frame: must have required property 'type'"`.

---

## CRITICAL: Method Name / Param Corrections vs plan.md

### chat.send params are WRONG in plan.md
```json
// WRONG (plan.md said):    {"sessionId": "...", "content": "..."}
// CORRECT (real API):
{"sessionKey": "agent:main:main", "message": "...", "idempotencyKey": "optional"}
// Returns:
{"runId": "...", "status": "started"}
```

### All session methods use `sessionKey`, not `sessionId`
`sessionKey` format: `"agent:main:main"` (agentId:name pattern)
`sessionId` is the UUID — used only inside session objects, NOT as an API parameter.

### cron.add params are WRONG in plan.md
```json
// WRONG (plan.md said): {"name":"...", "cron_expression":"...", "agent_id":"...", "query":"..."}
// CORRECT (real API):
{"name": "daily", "schedule": "0 9 * * *", "sessionTarget": "agent:main:main", "payload": "..."}
```

### `files.get` — NOW EXISTS as `agents.files.get`
The standalone `files.get` still does NOT exist (returns `"unknown method: files.get"`).
However, agent files are now accessible via `agents.files.get` with `{agentId, name}` params.
Also available: `agents.files.list` and `agents.files.set`.

### `approvals.*` — NOW EXISTS as `exec.approval.*` / `exec.approvals.*`
Previously unknown. Now 7 methods exist:
- `exec.approval.request`, `exec.approval.waitDecision`, `exec.approval.resolve`
- `exec.approvals.get`, `exec.approvals.set`, `exec.approvals.node.get`, `exec.approvals.node.set`

### `usage.*` — NOW EXISTS
Previously unknown. Now 3 methods exist:
- `usage.status`, `usage.cost`, `sessions.usage`

### `skills.*` — NOW GATEWAY METHODS
Previously CLI-only. Now 4 gateway methods exist:
- `skills.status`, `skills.bins`, `skills.install`, `skills.update`

### `webhooks.*` — STILL CLI-only (not in method list)
No change. Webhooks remain CLI-only integrations.

### `plugins.*` — STILL config-only
No change. Plugins are still configured in `openclaw.json`, not via gateway.

### `channels.list` — STILL use `channels.status` instead
No change. `channels.list` remains invalid.

---

## Verified Methods (93 total)

### agents.* (7 methods)
| Method | Required Params | Notes |
|--------|----------------|-------|
| `agents.list` | `{}` | Returns `{defaultId: str, mainKey: str, scope: str, agents: [{id: str}]}` — agent objects only have `id` field |
| `agents.create` | `{name, workspace}` | Create new agent |
| `agents.update` | `{agentId, ...patch}` | Update agent properties. NOTE: all agent IDs return "not found", may need internal ID |
| `agents.delete` | `{agentId}` | Delete agent |
| `agents.files.list` | `{agentId}` | Returns `{agentId, workspace, files: [{name, path, missing: bool, size: int, updatedAtMs: int}]}` |
| `agents.files.get` | `{agentId, name}` | Returns `{agentId, workspace, file: {name, path, missing, size, updatedAtMs, content: str}}` — name is case-sensitive exact filename |
| `agents.files.set` | `{agentId, name, content}` | Set agent file content |

### agent.* (3 methods)
| Method | Required Params | Notes |
|--------|----------------|-------|
| `agent` | `{message, idempotencyKey}` | Execution endpoint like chat.send, NOT a query |
| `agent.identity.get` | `{}` or `{agentId}` or `{sessionKey}` | Returns `{agentId, name, avatar, emoji?}` — emoji is optional. Defaults to default agent if `{}` |
| `agent.wait` | `{runId}` | Blocks until run completes (long-poll) |

### chat.* (4 methods)
| Method | Required Params | Notes |
|--------|----------------|-------|
| `chat.send` | `{sessionKey, message, idempotencyKey, attachments?, thinking?, deliver?, timeoutMs?}` | Returns `{runId, status:"started"}` |
| `chat.history` | `{sessionKey, limit?}` | Returns `{sessionKey, sessionId, messages:[...]}` |
| `chat.abort` | `{sessionKey}` | Abort running chat |
| `chat.inject` | `{sessionKey, message}` | Inject message into session |

**Message object shape (in chat.history)**:
```json
{
  "role": "user" | "assistant",
  "content": [{"type": "text", "text": "..."}, {"type": "thinking", "thinking": "..."}],
  "timestamp": 1771359478749,
  "api": "google-gemini-cli",
  "provider": "anthropic",
  "model": "claude-sonnet-4-5-thinking",
  "usage": {"input": 15669, "output": 334, "cacheRead": 0, "cacheWrite": 0, "totalTokens": 16003}
}
```

### sessions.* (8 methods)
| Method | Required Params | Notes |
|--------|----------------|-------|
| `sessions.list` | `{}` | Returns `{count, defaults, sessions:[...]}` |
| `sessions.preview` | `{keys: string[]}` | Session preview for given keys |
| `sessions.patch` | `{key, ...patch}` | Patch session |
| `sessions.reset` | `{key}` | Reset session |
| `sessions.delete` | `{key}` | Delete session |
| `sessions.compact` | `{key}` | Compact session |
| `sessions.resolve` | `{key}` or `{sessionId}` or `{label}` | NEW — resolve session by key, ID, or label |
| `sessions.usage` | `{}` | NEW — returns `{updatedAt, startDate, endDate, sessions:[...]}` |

**Session object shape**:
```json
{
  "key": "agent:main:main",
  "kind": "direct",
  "chatType": "direct",
  "sessionId": "dfe9835c-861e-45b8-80f0-a9882c8b8724",
  "updatedAt": 1771360111367,
  "systemSent": true,
  "abortedLastRun": false,
  "inputTokens": 3172,
  "outputTokens": 190,
  "totalTokens": 28746,
  "modelProvider": "anthropic",
  "model": "claude-opus-4-5",
  "contextTokens": 200000,
  "deliveryContext": {"channel": "webchat"},
  "lastChannel": "webchat"
}
```

### config.* (5 methods)
| Method | Required Params | Notes |
|--------|----------------|-------|
| `config.get` | `{}` | Returns `{path, exists, raw, parsed}` |
| `config.set` | full config object | Set entire config |
| `config.apply` | `{raw}` | NEW — apply config from raw string |
| `config.patch` | `{patch}` + optional `base_hash` | Patch config |
| `config.schema` | `{}` | Returns `{schema: {$schema, type, properties, ...}}` |

### cron.* (7 methods)
| Method | Required Params | Notes |
|--------|----------------|-------|
| `cron.list` | `{}` | Returns `{jobs: [...]}` |
| `cron.status` | `{}` | Returns `{enabled, storePath, ...}` |
| `cron.add` | `{name, schedule, sessionTarget, payload}` | Add cron job |
| `cron.update` | `{id/jobId, patch}` | Update cron job |
| `cron.remove` | `{id/jobId}` | Remove cron job |
| `cron.run` | `{id/jobId}` | Trigger cron job immediately |
| `cron.runs` | `{id/jobId}` | Get run history |

**IMPORTANT**: `schedule` is the cron expression field (not `cron_expression`).
`sessionTarget` is the session key (e.g. `"agent:main:main"`), not an agent_id.
`payload` is the message string to send (not `query`).

### channels.* (2 methods)
| Method | Required Params | Notes |
|--------|----------------|-------|
| `channels.status` | `{}` | Full channel status for all configured channels |
| `channels.logout` | `{channel}` | Logout from channel |

**channels.status response shape**:
```json
{
  "channelOrder": ["whatsapp"],
  "channelLabels": {"whatsapp": "WhatsApp"},
  "channels": {
    "whatsapp": {
      "configured": false, "linked": false, "authAgeMs": null,
      "self": {"e164": null, "jid": null},
      "running": false, "connected": false
    }
  }
}
```

### exec.approval.* (3 methods)
| Method | Required Params | Notes |
|--------|----------------|-------|
| `exec.approval.request` | `{command: str}`, optional: `{timeoutMs, agentId, sessionKey, nodeId}` | Returns `{id, decision, createdAtMs, expiresAtMs}`. Decision: "allow-once", "allow-always", "deny", or null (expired). BLOCKS until resolved. |
| `exec.approval.waitDecision` | `{id: str}` | Returns `{id, decision, createdAtMs, expiresAtMs}`. Loose schema (accepts extra params). |
| `exec.approval.resolve` | `{id, decision}` | Decision: "allow-once" \| "allow-always" \| "deny". Returns `{ok: true}`. |

### exec.approvals.* (4 methods)
| Method | Required Params | Notes |
|--------|----------------|-------|
| `exec.approvals.get` | `{}` | Returns `{path, exists, hash, file: {version: int, socket: {path}, defaults: {}, agents: {}}}`. No extra params accepted. |
| `exec.approvals.set` | `{file: {version: int, ...}, baseHash: str}` | Returns same shape as get. Uses optimistic concurrency via baseHash. |
| `exec.approvals.node.get` | `{nodeId: str}` | Proxied to node. Returns UNAVAILABLE if node not connected. |
| `exec.approvals.node.set` | `{nodeId: str, file: {version: int, ...}}`, optional: `{baseHash}` | Proxied to node. |

### device.* (6 methods)
| Method | Required Params | Notes |
|--------|----------------|-------|
| `device.pair.list` | `{}` | Returns `{pending: [], paired: [{deviceId, publicKey, platform, clientId, clientMode, role, roles: [], scopes: [], createdAtMs, approvedAtMs, tokens: [{role, scopes: [], createdAtMs, lastUsedAtMs}]}]}` |
| `device.pair.approve` | `{requestId}` | Approve device pairing request |
| `device.pair.reject` | `{requestId}` | Reject device pairing request |
| `device.pair.remove` | `{deviceId}` | Remove paired device |
| `device.token.rotate` | `{deviceId, role}` | Rotate device token |
| `device.token.revoke` | `{deviceId, role}` | Revoke device token |

### node.* (11 methods)
| Method | Required Params | Notes |
|--------|----------------|-------|
| `node.list` | `{}` | Returns `{ts, nodes: [...]}` |
| `node.describe` | TBD | Describe node capabilities |
| `node.rename` | `{nodeId, displayName}` | Rename a node |
| `node.invoke` | TBD | Invoke a node action |
| `node.invoke.result` | ROLE-RESTRICTED | Requires `node` role, not `operator` |
| `node.event` | ROLE-RESTRICTED | Requires `node` role, not `operator` |
| `node.pair.request` | `{nodeId}` | Request node pairing |
| `node.pair.list` | `{}` | Returns `{pending: [], paired: []}` |
| `node.pair.approve` | `{requestId}` | Approve node pairing |
| `node.pair.reject` | `{requestId}` | Reject node pairing |
| `node.pair.verify` | `{nodeId, token}` | Verify node pairing |

### usage.* (2 methods)
| Method | Required Params | Notes |
|--------|----------------|-------|
| `usage.status` | `{}` | Returns `{updatedAt, providers: [{provider, displayName, windows: [{label, usedPercent}], plan}]}` |
| `usage.cost` | `{}` | Returns `{updatedAt, days: int, daily: [{date, input, output, cacheRead, cacheWrite, totalTokens, totalCost, inputCost, outputCost, cacheReadCost, cacheWriteCost, missingCostEntries}], totals: {same fields minus date}}` |

Note: `sessions.usage` (listed under sessions.*) also returns usage data per session.

### tts.* (6 methods)
| Method | Required Params | Notes |
|--------|----------------|-------|
| `tts.status` | `{}` | Returns `{enabled, auto: "off"\|"on", provider, fallbackProvider, fallbackProviders: [], prefsPath, hasOpenAIKey, hasElevenLabsKey, edgeEnabled}` |
| `tts.providers` | `{}` | Returns `{providers: [{id, name, configured, models: [], voices: []}], active: str}` |
| `tts.enable` | `{}` | No params needed. Returns `{enabled: true}` |
| `tts.disable` | `{}` | No params needed. Returns `{enabled: false}` |
| `tts.convert` | `{text: str}` | Convert text to speech |
| `tts.setProvider` | `{provider: "openai"\|"elevenlabs"\|"edge"}` | Set active TTS provider |

### skills.* (4 methods)
| Method | Required Params | Notes |
|--------|----------------|-------|
| `skills.status` | `{}` | Returns `{workspaceDir, managedSkillsDir, skills: [{name, description, source, bundled, filePath, baseDir, skillKey, emoji?, homepage?, primaryEnv?, always, disabled, blockedByAllowlist, eligible, requirements: {bins, anyBins, env, config, os}, missing: {same}, configChecks: [{path, satisfied}], install: [{id, kind, label, bins}]}]}` |
| `skills.bins` | ROLE-RESTRICTED | Requires elevated privileges (not `operator` role) |
| `skills.install` | `{name, installId}` | Install a skill |
| `skills.update` | `{skillKey}` | Update a skill |

Note: These are NEW gateway methods as of post-2026.2.26. Previously skills were CLI-only.

### models & tools (2 methods)
| Method | Required Params | Notes |
|--------|----------------|-------|
| `models.list` | `{}` | Returns `{models: [{id, name, provider, contextWindow, reasoning, input: ["text"]\|["text","image"]}]}`. 300+ models across 19 providers. |
| `tools.catalog` | `{}` | Returns `{agentId, profiles: [{id, label}], groups: [{id, label, source, tools: [{id, label, description, source, defaultProfiles: []}]}]}` |

### wizard.* (4 methods)
| Method | Required Params | Notes |
|--------|----------------|-------|
| `wizard.start` | `{}` | Starts immediately. Returns `{sessionId, done: false, step: {type, title, message, executor, id}, status: "running"}` |
| `wizard.next` | `{sessionId}` | Advance to next wizard step |
| `wizard.cancel` | `{sessionId}` | Cancel the wizard |
| `wizard.status` | `{sessionId}` | NOT `{}` — requires a session ID |

### web.* (2 methods)
| Method | Required Params | Notes |
|--------|----------------|-------|
| `web.login.start` | `{channel}` | Returns `{qrDataUrl: "data:image/png;base64,..."}` |
| `web.login.wait` | `{channel, timeoutMs?}` | Waits for QR scan completion |

### System & misc (15 methods)
| Method | Required Params | Notes |
|--------|----------------|-------|
| `health` | `{}` | Health check |
| `status` | `{}` | Returns huge object: `{linkChannel: {id, label, linked, authAgeMs}, heartbeat: {defaultAgentId, agents: [{agentId, enabled, every, everyMs}]}, channelSummary: [], queuedSystemEvents: [], sessions: {paths, count, defaults: {model, contextTokens}, recent: [...], byAgent: [...]}}` |
| `doctor.memory.status` | `{}` | Returns `{agentId, provider, embedding: {ok, error?}}` |
| `logs.tail` | `{lines?}` | Tail logs, returns `{file, cursor, ...}` |
| `system-presence` | `{}` | Presence data for all nodes |
| `system-event` | `{text}` | Emit system event |
| `send` | `{to, idempotencyKey}` | Send a message |
| `browser.request` | `{method, path}` | Browser automation request |
| `wake` | `{mode, text}` | Wake agent from sleep |
| `last-heartbeat` | `{}` | Returns `{ts, status, reason, durationMs}` |
| `set-heartbeats` | `{enabled: bool}` | Configure heartbeat interval |
| `update.run` | `{}` | Safe: checks only. Returns `{ok, result: {status, mode, root, reason, before: {version}, steps, durationMs}, restart, sentinel}` |
| `secrets.reload` | `{}` | Returns `{ok, warningCount}` |
| `voicewake.get` | `{}` | Returns `{triggers: ["openclaw", "claude", "computer"]}` |
| `voicewake.set` | `{triggers: string[]}` | Set voice wake word config |

---

## Attachments (VERIFIED 2026-02-23)

**No server-side MIME allowlist** — the gateway accepts ANY MIME type.
The real constraint is the WebSocket frame size.

**Size limit**: Gateway `maxPayload` = **25 MiB** (26,214,400 bytes).
This was increased from 512 KiB in 2026.2.3-1 to 25 MiB in post-2026.2.26 builds.
After base64 encoding (~33% overhead) and the JSON envelope, the effective maximum
raw file size is approximately **18-19 MB**.

**Attachment payload format** (inside `chat.send` `attachments` array):
```json
{
  "type": "image",
  "mimeType": "image/png",
  "fileName": "screenshot.png",
  "content": "<base64-encoded-bytes>"
}
```

**Verified accepted MIME types** (all 28 tested accepted):
- Images: image/jpeg, image/png, image/gif, image/webp, image/svg+xml, image/heic
- Documents: application/pdf, text/plain, text/markdown, text/csv, application/json,
  application/vnd.openxmlformats-officedocument.wordprocessingml.document,
  application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
- Audio: audio/mpeg, audio/ogg, audio/wav, audio/webm, audio/mp4, audio/aac, audio/x-caf
- Video: video/mp4, video/webm, video/quicktime
- Exotic (also accepted): text/x-python, text/html, application/xml,
  application/zip, application/octet-stream

---

## INVALID Methods (do not implement as gateway calls)

These are either CLI-only or simply don't exist:
- `webhooks.*` — CLI-only integrations (Gmail Pub/Sub, etc.), not a generic API
- `plugins.*` — configured in `openclaw.json`, not via gateway RPC
- `channels.list` — use `channels.status` instead
- **Standalone `files.get`** — returns `"unknown method: files.get"`. Use `agents.files.get` instead.

### Non-Existent Methods (verified via live probes)
- `agents.get` — does NOT exist
- `agent.status` — does NOT exist
- `agent.identity.set` — does NOT exist
- `agents.files.delete` — does NOT exist
- `agent.files.list` — does NOT exist (use `agents.files.list` instead)

### Role-Restricted Methods
Some methods require elevated roles beyond `operator`:
- `skills.bins` — requires non-operator role
- `node.invoke.result` — requires `node` role
- `node.event` — requires `node` role

---

## Push Events (19 total, VERIFIED 2026-02-28)

| Event | When | Key Payload Fields |
|-------|------|--------------------|
| `connect.challenge` | Immediately on connect | `{nonce, ts}` |
| `agent` | During agent execution | `{runId, stream, data, sessionKey, seq}` |
| `chat` | Chat state changes | `{runId, sessionKey, state, message, seq}` |
| `presence` | Node presence changes | presence data |
| `tick` | Periodic keepalive | `{ts}` |
| `talk.mode` | Talk mode changes | talk mode data |
| `shutdown` | Server shutdown | shutdown data |
| `health` | Periodic health updates | `{ok, ts, channels, ...}` |
| `heartbeat` | Heartbeat events | heartbeat data |
| `cron` | Cron job events | `{action: "added"\|"updated"\|"removed"\|"started"\|"finished", ...}` |
| `node.pair.requested` | Node pairing request received | pairing request data |
| `node.pair.resolved` | Node pairing resolved | resolution data |
| `node.invoke.request` | Node invocation request | invocation data |
| `device.pair.requested` | Device pairing request received | pairing request data |
| `device.pair.resolved` | Device pairing resolved | resolution data |
| `voicewake.changed` | Voice wake word config changed | wake word data |
| `exec.approval.requested` | Approval requested (NEW) | approval request data |
| `exec.approval.resolved` | Approval resolved (NEW) | approval resolution data |
| `update.available` | System update available (NEW) | update info |

### Agent Execution Events
- `agent` with `stream: "lifecycle"`, `data.phase: "start"` — run started
- `agent` with `stream: "assistant"`, `data.delta: "..."` — streaming text
- `agent` with `stream: "lifecycle"`, `data.phase: "end"` — run ended
- `chat` with `state: "delta"` — content delta with `message.content`
- `chat` with `state: "final"` — complete response (terminal event)
- `chat` with `state: "aborted"` — run was aborted
- `chat` with `state: "error"` — run errored

### Chat Message Format
```json
{
  "message": {
    "role": "assistant",
    "content": [{"type": "text", "text": "Hello!"}],
    "timestamp": 1771664533174
  }
}
```

Push events envelope: `{"type":"event","event":"...","payload":{...}}`

---

## Protocol Limits

| Limit | Value | Notes |
|-------|-------|-------|
| `maxPayload` | **25 MiB** (26,214,400 bytes) | WebSocket frame size; was 512 KiB in 2026.2.3-1 |
| Protocol version | **3** | `minProtocol: 3, maxProtocol: 3` in connect params |

---

## SDK Model Corrections Required

Based on findings, these plan.md models need updating:

### ScheduleConfig
```python
class ScheduleConfig(BaseModel):
    name: str
    schedule: str          # was: cron_expression — real field name is "schedule"
    session_target: str    # was: agent_id — maps to gateway "sessionTarget"
    payload: str           # was: query — real field name is "payload"
    enabled: bool = True
```

### Agent execute — sessionKey awareness
The gateway identifies sessions by `sessionKey` (format: `"agent:main:main"`).

### SkillManager / ClawHub
Now that `skills.*` methods exist on the gateway (post-2026.2.26), the SDK can use
gateway RPC for `skills.status`, `skills.bins`, `skills.install`, `skills.update`.
The CLI subprocess fallback is still valid for older gateway versions.

### WebhookManager
Remove from v0.1.0 scope — there is no generic webhook gateway API.
Webhooks in OpenClaw are platform-specific integrations (Gmail, etc.) via CLI.

---

## Gateway Auth Token Location

```
~/.openclaw/openclaw.json -> gateway.auth.token
```

SDK should accept this as `OPENCLAW_GATEWAY_TOKEN` env var or `api_key` in ClientConfig.
