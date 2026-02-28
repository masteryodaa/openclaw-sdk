---
paths:
  - "src/openclaw_sdk/gateway/**/*.py"
  - "src/openclaw_sdk/core/client.py"
  - "src/openclaw_sdk/core/agent.py"
---

# Gateway Protocol Rules (verified against live OpenClaw dev build (post-2026.2.26))

IMPORTANT: Read `.claude/context/protocol-notes.md` for full verified protocol reference.

## Request Envelope
- All RPC requests MUST include `"type":"req"` field — gateway rejects without it
- Format: `{"type":"req", "id":"...", "method":"...", "params":{...}}`
- Gateway responses use `"payload"` NOT `"result"` field

## chat.send
- Params: `{sessionKey, message, thinking?, deliver?, attachments?, timeoutMs?, idempotencyKey}`
- `idempotencyKey` is MANDATORY (SDK auto-generates via uuid4)
- `thinking` param is a **string** NOT boolean — `"enabled"`, `"disabled"`, `"auto"`, or `"10000"`
- Attachments: `{type, mimeType, fileName, content}` base64, ANY MIME type, max ~375KB raw

## Session Keys
- Format: `"agent:{agent_id}:{session_name}"`
- All session methods use `{key}` NOT `{sessionKey}` — verified via live error
- `sessions.preview`: `{keys: string[]}` array NOT single key
- `sessions.patch`: `{key}` ONLY — extra fields rejected
- Session objects use `"key"` field NOT `"sessionKey"`

## Methods That DO NOT EXIST
- Standalone `files.get` doesn't exist — use `agents.files.get` instead
- `webhooks.*` — CLI-only, NOT gateway RPC
- `plugins.*` — not exposed via gateway

## Gateway Capacity
- maxPayload increased to 25 MiB (was 512 KiB)
- 93 methods now available (was ~30)

## Auth Flow
- connect → receive `connect.challenge` → respond with `connect` RPC (Ed25519 signature)
- Client constants: `client.id="cli"`, `client.mode="cli"` (schema-validated)
- Device identity: `~/.openclaw/identity/device.json` + `device-auth.json`
