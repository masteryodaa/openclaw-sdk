# Dashboard

The OpenClaw SDK includes a full-featured FastAPI admin backend for managing your
OpenClaw deployment. The dashboard exposes REST API endpoints for agents, sessions,
configuration, metrics, webhooks, workflows, audit logs, billing, templates,
connectors, schedules, and channels -- all wired to your `OpenClawClient` instance.

Install the dashboard extra to get started:

```bash
pip install openclaw-sdk[dashboard]
```

## Quick Start

```python
import asyncio
import uvicorn
from openclaw_sdk import OpenClawClient
from openclaw_sdk.dashboard import create_dashboard_app

async def main():
    client = await OpenClawClient.connect("ws://127.0.0.1:18789/gateway")

    app = create_dashboard_app(client)
    config = uvicorn.Config(app, host="0.0.0.0", port=8000)
    server = uvicorn.Server(config)
    await server.serve()

asyncio.run(main())
```

Once running, visit `http://localhost:8000/docs` for the auto-generated Swagger UI,
or `http://localhost:8000/redoc` for ReDoc documentation.

## App Factory

The `create_dashboard_app()` function is the single entry point. It creates a FastAPI
application, attaches the client and optional managers to `app.state`, and includes
all 13 routers.

```python
from openclaw_sdk.dashboard import create_dashboard_app
from openclaw_sdk.webhooks.manager import WebhookManager
from openclaw_sdk.tracking.cost import CostTracker

app = create_dashboard_app(
    client,
    audit_logger=my_audit_logger,
    billing_manager=my_billing_manager,
    webhook_manager=WebhookManager(),
    cost_tracker=CostTracker(),
)
```

| Parameter          | Type                      | Default | Description                                    |
|--------------------|---------------------------|---------|------------------------------------------------|
| `client`           | `OpenClawClient`          | *required* | A connected client instance                 |
| `audit_logger`     | `AuditLogger \| None`     | `None`  | Optional audit logger for audit endpoints      |
| `billing_manager`  | `BillingManager \| None`  | `None`  | Optional billing manager for billing endpoints |
| `webhook_manager`  | `WebhookManager \| None`  | `None`  | Optional webhook manager for webhook endpoints |
| `cost_tracker`     | `CostTracker \| None`     | `None`  | Optional cost tracker for metrics endpoints    |

!!! note "Optional managers"
    Routers for audit, billing, webhooks, and metrics return HTTP 404 if their
    corresponding manager is not provided. All other routers work with just the
    `client` parameter.

## Routers Overview

The dashboard includes 13 routers organized by feature area. Each router is
automatically included when you call `create_dashboard_app()`.

### Health

| Method | Endpoint          | Description                     |
|--------|-------------------|---------------------------------|
| `GET`  | `/api/health`     | Check gateway health status     |

Returns the gateway's health status including `healthy`, `latency_ms`, `version`,
and `details`.

### Agents

| Method | Endpoint                           | Description                       |
|--------|------------------------------------|-----------------------------------|
| `POST` | `/api/agents/{agent_id}/execute`   | Execute a query against an agent  |
| `GET`  | `/api/agents/{agent_id}/status`    | Get current agent status          |

The execute endpoint accepts a JSON body with `query`, `session_name` (default
`"main"`), and `timeout_seconds` (default `300`).

### Sessions

| Method   | Endpoint                          | Description                     |
|----------|-----------------------------------|---------------------------------|
| `GET`    | `/api/sessions/{key}/preview`     | Preview a session               |
| `POST`   | `/api/sessions/{key}/reset`       | Reset session history           |
| `DELETE` | `/api/sessions/{key}`             | Delete a session permanently    |

Session keys use the format `agent:{agent_id}:{session_name}`.

### Config

| Method  | Endpoint       | Description                            |
|---------|----------------|----------------------------------------|
| `GET`   | `/api/config`  | Get current runtime configuration      |
| `PUT`   | `/api/config`  | Replace entire config (`config.set`)   |
| `PATCH` | `/api/config`  | Patch config with compare-and-swap     |

The `PUT` endpoint accepts `{"raw": "..."}` with the full config JSON string.
The `PATCH` endpoint accepts `{"raw": "...", "base_hash": "..."}` for safe
concurrent updates.

### Metrics

| Method | Endpoint             | Description                   |
|--------|----------------------|-------------------------------|
| `GET`  | `/api/metrics/costs` | Return cost summary from CostTracker |

Requires a `CostTracker` to be provided to `create_dashboard_app()`.

### Webhooks

| Method   | Endpoint                | Description                           |
|----------|-------------------------|---------------------------------------|
| `GET`    | `/api/webhooks`         | List all registered webhooks          |
| `POST`   | `/api/webhooks`         | Register a new webhook                |
| `DELETE` | `/api/webhooks/{name}`  | Unregister a webhook by name          |
| `POST`   | `/api/webhooks/fire`    | Fire a test event to matching webhooks |

Requires a `WebhookManager` to be provided to `create_dashboard_app()`.

### Workflows

| Method | Endpoint                         | Description                        |
|--------|----------------------------------|------------------------------------|
| `GET`  | `/api/workflows/presets`         | List available workflow presets     |
| `POST` | `/api/workflows/{preset}/run`    | Run a preset workflow              |

The run endpoint accepts `{"args": {"agent_id_1": "...", ...}, "context": {...}}`.
Available presets: `review`, `research`, `support`.

### Audit

| Method | Endpoint      | Description                                  |
|--------|---------------|----------------------------------------------|
| `GET`  | `/api/audit`  | Query audit log entries with optional filters |

Query parameters: `event_type`, `agent_id`, `limit` (1-1000, default 100).
Requires an `AuditLogger` to be provided.

### Billing

| Method | Endpoint                           | Description                         |
|--------|------------------------------------|-------------------------------------|
| `GET`  | `/api/billing/usage`               | Get usage summary for a tenant      |
| `GET`  | `/api/billing/invoice/{tenant_id}` | Generate an invoice for a tenant    |

Query parameters for usage: `tenant_id` (required). Invoice supports optional
`period_start` and `period_end` as ISO-8601 date strings. Requires a
`BillingManager` to be provided.

### Templates

| Method | Endpoint                  | Description                   |
|--------|---------------------------|-------------------------------|
| `GET`  | `/api/templates`          | List available template names |
| `GET`  | `/api/templates/{name}`   | Get template details by name  |

### Connectors

| Method | Endpoint           | Description                       |
|--------|--------------------|-----------------------------------|
| `GET`  | `/api/connectors`  | List available connector classes  |

### Schedules

| Method   | Endpoint                     | Description                   |
|----------|------------------------------|-------------------------------|
| `GET`    | `/api/schedules`             | List all scheduled cron jobs  |
| `DELETE` | `/api/schedules/{job_id}`    | Delete a schedule by job ID   |

### Channels

| Method | Endpoint               | Description               |
|--------|------------------------|---------------------------|
| `GET`  | `/api/channels/status` | Get all channel statuses  |

## Customization

Since `create_dashboard_app()` returns a standard `FastAPI` application, you can
customize it like any other FastAPI app:

### Adding custom routes

```python
from fastapi import FastAPI
from openclaw_sdk.dashboard import create_dashboard_app

app = create_dashboard_app(client)

@app.get("/api/custom/hello")
async def custom_hello():
    return {"message": "Hello from my custom endpoint"}
```

### Adding middleware

```python
from fastapi.middleware.cors import CORSMiddleware

app = create_dashboard_app(client)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Adding authentication

```python
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    if credentials.credentials != "my-secret-token":
        raise HTTPException(status_code=401, detail="Invalid token")

app = create_dashboard_app(client)

# Protect all routes
for route in app.routes:
    if hasattr(route, "dependant"):
        route.dependant.dependencies.append(Depends(verify_token))
```

### Mounting under a prefix

```python
from fastapi import FastAPI

main_app = FastAPI()
dashboard = create_dashboard_app(client)
main_app.mount("/dashboard", dashboard)
```

!!! tip "Swagger UI"
    The dashboard ships with FastAPI's built-in Swagger UI at `/docs` and ReDoc at
    `/redoc`. These provide interactive API documentation where you can test
    endpoints directly from your browser.

!!! warning "Production deployment"
    The dashboard does not include authentication or rate limiting by default.
    For production deployments, add authentication middleware, CORS configuration,
    and rate limiting before exposing the dashboard to the network.
