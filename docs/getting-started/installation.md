# Installation

## Requirements

- **Python 3.11** or newer
- A running **OpenClaw** instance (local or remote)

## Install from PyPI

```bash
pip install openclaw-sdk
```

### With FastAPI Integration

If you want to use the built-in FastAPI routers:

```bash
pip install "openclaw-sdk[fastapi]"
```

### With Poetry

```bash
poetry add openclaw-sdk
```

## Verify Installation

```python
import openclaw_sdk
print(openclaw_sdk.__version__)
```

## Dependencies

The SDK has minimal runtime dependencies:

| Package | Purpose |
|---------|---------|
| `pydantic >= 2.0` | Config models, validation, serialization |
| `websockets >= 12.0` | WebSocket transport to OpenClaw gateway |
| `httpx >= 0.25` | HTTP transport (OpenAI-compatible mode) |
| `structlog >= 23.0` | Structured logging |

Optional:

| Package | Purpose |
|---------|---------|
| `fastapi >= 0.100` | FastAPI router integration |
| `uvicorn >= 0.23` | ASGI server for FastAPI |

## OpenClaw Setup

The SDK connects to an OpenClaw gateway. Make sure you have OpenClaw running:

=== "Local (default)"

    OpenClaw running locally is auto-detected at `ws://127.0.0.1:18789/gateway`.
    No configuration needed.

=== "Remote"

    Set the gateway URL via environment variable:

    ```bash
    export OPENCLAW_GATEWAY_WS_URL=ws://my-server:18789/gateway
    export OPENCLAW_API_KEY=your-api-key
    ```

=== "OpenAI-Compatible"

    For OpenAI-compatible HTTP endpoints:

    ```bash
    export OPENCLAW_OPENAI_BASE_URL=http://my-server:8080/v1
    export OPENCLAW_API_KEY=your-api-key
    ```

## Compatibility Matrix

| openclaw-sdk | Python | OpenClaw | pydantic |
|-------------|--------|----------|----------|
| 0.2.x | 3.11, 3.12, 3.13 | 2026.2.0+ | >= 2.0 |
| 0.1.x | 3.11, 3.12 | 2026.2.0+ | >= 2.0 |

## Next Steps

- [Quickstart](quickstart.md) — connect and run your first agent
- [Configuration](configuration.md) — all configuration options
