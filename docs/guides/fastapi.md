# FastAPI Integration

The OpenClaw SDK provides optional FastAPI router factories that expose your agents,
channels, and admin operations as REST endpoints. This lets you wrap your agent
infrastructure in a standard HTTP API with minimal boilerplate.

## Installation

The FastAPI integration requires additional dependencies. Install them with the
`fastapi` extra:

```bash
pip install "openclaw-sdk[fastapi]"
```

This pulls in `fastapi` and `uvicorn` alongside the core SDK.

## Quick Start

```python
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from openclaw_sdk import OpenClawClient
from openclaw_sdk.integrations.fastapi import (
    create_agent_router,
    create_channel_router,
    create_admin_router,
)

client: OpenClawClient | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global client
    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as c:
        client = c
        yield
    client = None

app = FastAPI(title="OpenClaw API", lifespan=lifespan)

app.include_router(create_agent_router(lambda: client, prefix="/agents"))
app.include_router(create_channel_router(lambda: client, prefix="/channels"))
app.include_router(create_admin_router(lambda: client, prefix="/admin"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

!!! note "Client factory pattern"
    The router factories accept a callable (`lambda: client`) rather than a
    direct client reference. This is because the client is not available until
    the application lifespan starts. The callable is invoked on each request.

## Router Reference

### Agent Router

Created with `create_agent_router(client_factory, prefix="/agents")`.

| Method | Path                      | Description                            |
|--------|---------------------------|----------------------------------------|
| GET    | `/agents/health`          | Gateway health check                   |
| POST   | `/agents/{id}/execute`    | Execute a query against an agent       |

**Execute request body:**

```json
{
    "query": "What is the weather today?",
    "session": "optional-session-name"
}
```

**Execute response:**

```json
{
    "output": "The weather today is...",
    "latency_ms": 1234,
    "model": "claude-sonnet-4-20250514",
    "input_tokens": 42,
    "output_tokens": 156
}
```

### Channel Router

Created with `create_channel_router(client_factory, prefix="/channels")`.

| Method | Path                            | Description                        |
|--------|---------------------------------|------------------------------------|
| GET    | `/channels/status`              | List all channels and their status |
| POST   | `/channels/{ch}/logout`         | Log out of a channel               |
| POST   | `/channels/{ch}/login/start`    | Start the login flow               |
| POST   | `/channels/{ch}/login/wait`     | Wait for login completion          |

!!! tip "Channel login flow"
    Channel login is a two-step process. First call `/login/start` to initiate
    the flow (this may return a QR code or auth URL). Then call `/login/wait`
    to block until the login completes or times out.

### Admin Router

Created with `create_admin_router(client_factory, prefix="/admin")`.

| Method | Path                             | Description                       |
|--------|----------------------------------|-----------------------------------|
| GET    | `/admin/schedules`               | List all scheduled tasks          |
| DELETE | `/admin/schedules/{id}`          | Delete a scheduled task           |
| GET    | `/admin/skills`                  | List installed skills             |
| POST   | `/admin/skills/{name}/install`   | Install a skill from ClawHub      |

## Usage Examples

### Health Check

```bash
curl http://localhost:8000/agents/health
```

```json
{"status": "healthy", "gateway": "connected"}
```

### Execute an Agent

```bash
curl -X POST http://localhost:8000/agents/assistant/execute \
  -H "Content-Type: application/json" \
  -d '{"query": "Summarize the latest AI news"}'
```

### Channel Status

```bash
curl http://localhost:8000/channels/status
```

```json
{
    "channels": [
        {"name": "whatsapp", "status": "connected", "uptime_seconds": 3600},
        {"name": "telegram", "status": "disconnected"}
    ]
}
```

### List Schedules

```bash
curl http://localhost:8000/admin/schedules
```

## Adding Authentication

The routers are standard FastAPI routers, so you can add dependencies for
authentication:

```python
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_token(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> str:
    if credentials.credentials != "my-secret-token":
        raise HTTPException(status_code=401, detail="Invalid token")
    return credentials.credentials

# Protected agent router
agent_router = create_agent_router(lambda: client, prefix="/agents")
app.include_router(agent_router, dependencies=[Depends(verify_token)])
```

!!! warning "Secure your endpoints"
    The routers do not include authentication by default. In production,
    always add authentication middleware or dependencies to prevent
    unauthorized access to your agents and admin operations.

## Complete Application

```python
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from openclaw_sdk import OpenClawClient
from openclaw_sdk.integrations.fastapi import (
    create_agent_router,
    create_channel_router,
    create_admin_router,
)

security = HTTPBearer()

async def verify_token(
    creds: HTTPAuthorizationCredentials = Security(security),
) -> str:
    if creds.credentials != "my-secret-token":
        raise HTTPException(status_code=401, detail="Unauthorized")
    return creds.credentials

client: OpenClawClient | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global client
    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as c:
        client = c
        yield
    client = None

app = FastAPI(title="OpenClaw API", version="1.0.0", lifespan=lifespan)
auth = [Depends(verify_token)]

app.include_router(create_agent_router(lambda: client, prefix="/agents"), dependencies=auth)
app.include_router(create_channel_router(lambda: client, prefix="/channels"), dependencies=auth)
app.include_router(create_admin_router(lambda: client, prefix="/admin"), dependencies=auth)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```
