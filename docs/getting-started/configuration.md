# Configuration

## Connection Options

`OpenClawClient.connect()` accepts these parameters:

| Parameter | Env Var | Default | Description |
|-----------|---------|---------|-------------|
| `gateway_ws_url` | `OPENCLAW_GATEWAY_WS_URL` | — | WebSocket gateway URL |
| `openai_base_url` | `OPENCLAW_OPENAI_BASE_URL` | — | OpenAI-compatible HTTP URL |
| `api_key` | `OPENCLAW_API_KEY` | — | Authentication key |
| `timeout` | — | `300` | Default execution timeout (seconds) |
| `mode` | — | `"auto"` | Gateway selection mode |

### Gateway Auto-Detection

When `mode="auto"` (the default), the SDK tries these in order:

1. **WebSocket** — if `OPENCLAW_GATEWAY_WS_URL` is set
2. **OpenAI-compatible** — if `OPENCLAW_OPENAI_BASE_URL` is set
3. **Local** — probes `127.0.0.1:18789` for a local OpenClaw instance

### Explicit Configuration

=== "Environment Variables"

    ```bash
    export OPENCLAW_GATEWAY_WS_URL=ws://my-server:18789/gateway
    export OPENCLAW_API_KEY=your-api-key
    ```

    ```python
    async with OpenClawClient.connect() as client:
        ...  # picks up env vars automatically
    ```

=== "Direct Parameters"

    ```python
    async with OpenClawClient.connect(
        gateway_ws_url="ws://my-server:18789/gateway",
        api_key="your-api-key",
        timeout=60,
    ) as client:
        ...
    ```

=== "ClientConfig Object"

    ```python
    from openclaw_sdk import ClientConfig, OpenClawClient

    config = ClientConfig(
        gateway_ws_url="ws://my-server:18789/gateway",
        api_key="your-api-key",
        timeout=60,
    )
    async with OpenClawClient.connect(
        **config.model_dump(exclude_none=True)
    ) as client:
        ...
    ```

## ClientConfig

The `ClientConfig` Pydantic model holds all client configuration:

```python
from openclaw_sdk import ClientConfig

config = ClientConfig(
    gateway_ws_url="ws://localhost:18789/gateway",
    api_key="secret",
    timeout=120,
    mode="auto",
)
```

## AgentConfig

Configure agent-level settings:

```python
from openclaw_sdk import AgentConfig
from openclaw_sdk.memory.config import MemoryConfig

config = AgentConfig(
    agent_id="research-bot",
    name="Research Bot",
    model="claude-sonnet-4-20250514",
    system_prompt="You are a research assistant.",
    memory=MemoryConfig(backend="persistent", scope="agent"),
)
```

## ExecutionOptions

Per-execution settings passed to `agent.execute()`:

```python
from openclaw_sdk import ExecutionOptions, Attachment

options = ExecutionOptions(
    timeout_seconds=600,       # Override timeout
    stream=False,              # Sync mode
    max_tool_calls=100,        # Tool call limit
    thinking=True,             # Enable thinking mode
    deliver=False,             # Don't deliver to channel
    attachments=[              # Attach images
        Attachment.from_path("screenshot.png"),
    ],
)

result = await agent.execute("Analyze this image", options=options)
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `timeout_seconds` | `int` | `300` | Execution timeout (1–3600) |
| `stream` | `bool` | `False` | Enable streaming mode |
| `max_tool_calls` | `int` | `50` | Maximum tool calls (1–200) |
| `thinking` | `bool` | `False` | Enable thinking/reasoning mode |
| `deliver` | `bool \| None` | `None` | Deliver to channel (`None` = gateway default) |
| `attachments` | `list` | `[]` | File attachments (images, max 5MB each) |

## Gateway Modes

| Mode | Class | Transport | Use Case |
|------|-------|-----------|----------|
| `"websocket"` | `ProtocolGateway` | WebSocket | Remote or local OpenClaw |
| `"openai"` | `OpenAICompatGateway` | HTTP | OpenAI-compatible endpoints |
| `"local"` | `LocalGateway` | WebSocket | Local dev (auto-connect) |
| `"auto"` | — | Auto-detect | Production default |

!!! tip "Testing"
    For unit tests, use `MockGateway` — an in-memory gateway that doesn't
    need a real OpenClaw instance:

    ```python
    from openclaw_sdk.gateway.mock import MockGateway

    gateway = MockGateway()
    client = OpenClawClient(gateway=gateway)
    ```

## Compatibility Metadata

The SDK declares which OpenClaw versions it supports:

```python
import openclaw_sdk

print(openclaw_sdk.__openclaw_compat__)
# {'min': '2026.2.0', 'max_tested': '2026.2.3-1'}
```

## Next Steps

- [Agents & Execution](../guides/agents.md) — using agents
- [Tool Policy](../guides/tool-policy.md) — controlling agent tools
- [FastAPI Integration](../guides/fastapi.md) — web API setup
