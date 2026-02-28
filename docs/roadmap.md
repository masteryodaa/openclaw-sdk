# Roadmap

This page outlines planned features and the broader **OpenClaw ecosystem** vision for `openclaw-sdk`.

---

## v2.1 — CLI Init Wizard

**Goal:** Zero-friction setup — `pip install openclaw-sdk` then one command to configure everything.

Inspired by `npm init`, `create-react-app`, and `poetry new`, the SDK will ship a built-in CLI:

```bash
pip install openclaw-sdk
openclaw-sdk init
```

The wizard will walk you through interactive prompts:

```
? Gateway URL [ws://127.0.0.1:18789/gateway]:
? Agent ID [main]:
? Default model provider (anthropic/openai/gemini/ollama) [anthropic]:
? Default model [claude-opus-4-6]:
? Enable cost tracking? [Y/n]:
? Session name [main]:
? Output config to [~/.openclaw/sdk-config.json]:

✔ Config written to ~/.openclaw/sdk-config.json
✔ Connection verified — gateway healthy (OpenClaw post-2026.2.26)

You're ready! Try:

  python -c "
  import asyncio
  from openclaw_sdk import OpenClawClient

  async def main():
      async with OpenClawClient.connect() as client:
          agent = client.get_agent('main')
          result = await agent.execute('Hello!')
          print(result.content)

  asyncio.run(main())
  "
```

**Implementation plan:**

- Built on `typer` + `questionary` (Windows-compatible interactive prompts)
- Registered as `openclaw-sdk` console script in `pyproject.toml`
- Auto-detects existing OpenClaw config at `~/.openclaw/openclaw.json`
- Validates gateway connectivity before writing config
- Generates a minimal `sdk-config.json` that `ClientConfig.from_env()` reads automatically

**Sub-commands planned:**

| Command | Description |
|---|---|
| `openclaw-sdk init` | Interactive setup wizard |
| `openclaw-sdk new` | Create a new project (prompt or template) |
| `openclaw-sdk verify` | Test gateway connection and print health |
| `openclaw-sdk agents` | List available agents |
| `openclaw-sdk chat <agent>` | REPL chat directly from terminal |
| `openclaw-sdk version` | Print SDK + gateway versions |

### `openclaw-sdk new` — Project Scaffolding

No external tools required — just the SDK and your OpenClaw gateway.

Run `openclaw-sdk new` and pick how you want to start:

```
? How do you want to start?
  > From a prompt   — describe your idea, SDK scaffolds the project
    From a template — pick a base starter
    Empty project   — bare minimum, just connect and go
```

---

**Option 1 — From a prompt**

Describe what you want to build. The SDK sends the prompt to your OpenClaw agent,
which plans and writes the project files directly into a local directory:

```bash
openclaw-sdk new

? How do you want to start? From a prompt
? Describe your project: A REST API with FastAPI, SQLite, and JWT auth
? Project name [my-project]: my-api

⠋ Agent is planning your project...
⠋ Writing files...

✔ Created my-api/
  ├── main.py
  ├── requirements.txt
  ├── app/
  │   ├── routers/
  │   ├── models/
  │   └── auth/
  └── README.md

Run:  cd my-api && pip install -r requirements.txt && python main.py
```

---

**Option 2 — From a template**

Pick a pre-built starter. No AI needed, just instant boilerplate:

```bash
openclaw-sdk new

? How do you want to start? From a template
? Choose a template:
  > empty          — bare OpenClawClient setup
    rest-api       — FastAPI + SQLite starter
    chatbot        — conversational agent starter
    data-pipeline  — ETL pipeline with structured output
    multi-agent    — Pipeline + Supervisor pattern
    full-stack     — FastAPI backend + Next.js frontend
? Project name: my-chatbot

✔ Created my-chatbot/ from template: chatbot
Run:  cd my-chatbot && pip install -r requirements.txt && python main.py
```

---

**Option 3 — Empty project**

Minimal scaffold — just the SDK wired up, nothing else:

```bash
openclaw-sdk new

? How do you want to start? Empty project
? Project name: my-project

✔ Created my-project/
  ├── main.py           # OpenClawClient.connect() ready to go
  ├── requirements.txt  # openclaw-sdk pinned
  └── .env.example      # OPENCLAW_GATEWAY_URL, OPENCLAW_API_KEY
```

---

## v2.2 — New Gateway Method Coverage (93 methods discovered)

**Goal:** Wrap the 60+ newly discovered gateway methods that were previously unknown or invalid.

As of 2026-02-28, a full gateway probe revealed **93 RPC methods** and **19 event types** -- far more than the ~30 originally documented. Many methods previously thought to be invalid (agents.*, exec.approval.*, usage.*, skills.*) are now confirmed working on post-2026.2.26 builds.

### Agent CRUD Management

Full lifecycle management of agents via `agents.list`, `agents.get`, `agents.create`, `agents.update`, `agents.delete`, `agents.duplicate`, `agents.export`:

```python
agents = await client.agents.list()
new_agent = await client.agents.create(name="researcher", model="claude-opus-4-6")
await client.agents.update(agent_id, instructions="You are a research assistant.")
await client.agents.delete(agent_id)
```

### Agent Files API

Read and write agent workspace files via `agents.files.list`, `agents.files.get`, `agents.files.set`:

```python
files = await agent.files.list()
content = await agent.files.get("notes.md")
await agent.files.set("config.json", '{"key": "value"}')
```

### Execution Approval System

Full approval workflow via `exec.approval.list`, `exec.approval.get`, `exec.approval.resolve`, `exec.approval.resolveAll`, `exec.approval.config.get`, `exec.approval.config.set`, `exec.approval.autoRules.list`:

```python
pending = await client.approvals.list()
await client.approvals.resolve(approval_id, action="approve")
await client.approvals.resolve_all(agent_id, action="approve")
```

### Usage Tracking

Monitor cost and usage via `usage.status`, `usage.cost`, and `sessions.usage`:

```python
status = await client.usage.status()
costs = await client.usage.cost(period="month")
session_usage = await agent.session_usage(session_key)
```

### Skills Management via Gateway

Install, list, and manage skills via `skills.list`, `skills.get`, `skills.install`, `skills.remove`:

```python
installed = await client.skills.list()
await client.skills.install("web-search")
await client.skills.remove("unused-skill")
```

### TTS Integration

Text-to-speech via gateway: `tts.speak`, `tts.stop`, `tts.voices`, `tts.status`, `tts.config.get`, `tts.config.set`:

```python
voices = await client.tts.voices()
await client.tts.speak(text="Hello world", voice="alloy")
await client.tts.stop()
```

### Models & Tools Discovery

Discover available models and tool catalogs via `models.list` and `tools.catalog`:

```python
models = await client.models.list()
tools = await client.tools.catalog()
```

### Device Management

Enhanced device operations via `device.list`, `device.info`, `device.remove`, `device.token.rotate`, `device.token.revoke`, `device.setName`:

```python
devices = await client.devices.list()
await client.devices.rotate_token(device_id)
await client.devices.set_name(device_id, "my-server")
```

---

## v2.3 — Ecosystem: OpenClaw Claw Suite

The SDK will add first-class support for the broader **OpenClaw ecosystem**:

### ClawForge Integration
Native Python client for ClawForge (the AI app builder live example) — the AI app builder:

```python
from openclaw_sdk.integrations.clawforge import ClawForgeClient

async with ClawForgeClient.connect("http://127.0.0.1:8200") as cf:
    project = await cf.create_project("Build a REST API with FastAPI")
    async for event in cf.stream_build(project.id):
        print(event)
```

### ClawHub Skills Marketplace
Install and manage OpenClaw skills directly from Python:

```python
from openclaw_sdk.skills import ClawHub

hub = ClawHub()
await hub.install("web-search")
await hub.install("github-actions")
skills = await hub.list_installed()
```

### Multi-Gateway Federation
Connect to multiple OpenClaw instances (local + remote) with automatic routing:

```python
client = await OpenClawClient.connect(
    gateways=[
        "ws://127.0.0.1:18789/gateway",   # local
        "wss://cloud.openclaw.ai/gateway", # remote
    ],
    routing="least-loaded"
)
```

### TypeScript/Node.js Bridge
Call OpenClaw's native Node.js API from Python when gateway RPC is insufficient:

```python
from openclaw_sdk.bridge import NodeBridge

bridge = NodeBridge()
result = await bridge.call("skills.list")  # calls Node.js SDK directly
```

---

## v2.4 — Remote File Access

Once the OpenClaw gateway implements `files.get` RPC, the SDK will expose:

```python
# Currently raises GatewayError (not implemented in gateway ≤ post-2026.2.26)
# Will work transparently once the gateway ships the method:
file_bytes = await agent.get_file("output/report.pdf")
```

No SDK changes needed — `Agent.get_file()` is already forward-compatible.
The gateway just needs to ship the implementation.

---

## v2.5 — Agent Marketplace

Discover and run community-published agent configs:

```python
from openclaw_sdk.marketplace import AgentMarketplace

market = AgentMarketplace()
templates = await market.search("data analyst")
await market.deploy(templates[0], agent_id="analyst")
```

---

## v3.0 — OpenClaw SDK for Other Languages

The long-term vision is a **unified SDK family** across languages, all wrapping the same OpenClaw gateway protocol:

| SDK | Status |
|---|---|
| `openclaw-sdk` (Python) | ✅ Available — `pip install openclaw-sdk` |
| `@openclaw/sdk` (TypeScript/Node.js) | 🔜 Planned |
| `openclaw-sdk` (Go) | 🔜 Planned |
| `openclaw-sdk` (Rust) | 🔜 Planned |

All SDKs will share the same gateway protocol, auth flow, and session model.

---

## Community & Contributions

Want to help build any of these? See the [Contributing Guide](https://github.com/masteryodaa/openclaw-sdk/blob/main/CONTRIBUTING.md).

Open feature requests and discussion at: [GitHub Issues](https://github.com/masteryodaa/openclaw-sdk/issues)
