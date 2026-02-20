# RUN: python examples/03_fastapi_backend.py
"""FastAPI backend — create agent, channel, and admin routers backed by MockGateway.

Demonstrates: create_agent_router(), create_channel_router(), create_admin_router(),
and the full set of SDK routers available for FastAPI integration.

Run the server with:
    uvicorn examples.03_fastapi_backend:app --reload

Then test with:
    curl -X POST http://localhost:8000/agents/greeter/execute \
         -H "Content-Type: application/json" \
         -d '{"query": "Say hello"}'
"""

import asyncio

from openclaw_sdk import OpenClawClient, ClientConfig, EventType
from openclaw_sdk.core.types import StreamEvent
from openclaw_sdk.gateway.mock import MockGateway

try:
    from fastapi import FastAPI
    from openclaw_sdk.integrations.fastapi import (
        create_admin_router,
        create_agent_router,
        create_channel_router,
    )

    _FASTAPI_AVAILABLE = True
except ImportError:
    _FASTAPI_AVAILABLE = False


# ---------------------------------------------------------------------------
# Build the app (only when FastAPI is installed)
# ---------------------------------------------------------------------------

if _FASTAPI_AVAILABLE:
    app = FastAPI(title="OpenClaw SDK Demo", version="0.1.0")

    _client: OpenClawClient | None = None

    @app.on_event("startup")
    async def _startup() -> None:
        global _client
        mock = MockGateway()
        mock.register(
            "chat.send",
            lambda _params: {"runId": "demo-run", "status": "started"},
        )
        mock.register("channels.status", {
            "channelOrder": ["whatsapp"],
            "channels": {"whatsapp": {"configured": False, "linked": False}},
        })
        mock.register("sessions.list", {"count": 0, "sessions": []})
        await mock.connect()
        mock.emit_event(
            StreamEvent(
                event_type=EventType.DONE,
                data={"payload": {"runId": "demo-run", "content": "Hello from MockGateway!"}},
            )
        )
        _client = OpenClawClient(config=ClientConfig(), gateway=mock)
        # Attach all three routers: agents, channels, admin
        app.include_router(create_agent_router(_client, prefix="/agents"))
        app.include_router(create_channel_router(_client, prefix="/channels"))
        app.include_router(create_admin_router(_client, prefix="/admin"))

    @app.get("/")
    async def root() -> dict:
        return {
            "message": "OpenClaw SDK FastAPI demo",
            "note": "Uses MockGateway — no live OpenClaw required",
            "endpoints": {
                "agents": [
                    "GET  /agents/health",
                    "POST /agents/{agent_id}/execute",
                ],
                "channels": [
                    "GET  /channels/status",
                    "POST /channels/{name}/login",
                ],
                "admin": [
                    "GET  /admin/skills",
                    "GET  /admin/schedules",
                ],
            },
        }


async def main() -> None:
    if _FASTAPI_AVAILABLE:
        print("FastAPI app created successfully.")
        print("Registered routes (before startup):")
        for route in app.routes:  # type: ignore[union-attr]
            if hasattr(route, "path"):
                print(f"  {route.path}")  # type: ignore[attr-defined]
        print("\nRun with: uvicorn examples.03_fastapi_backend:app --reload")
        print("Note: Uses MockGateway — no live OpenClaw instance required.")
    else:
        print("FastAPI is not installed.")
        print("Install with: pip install fastapi uvicorn")
        print("Then run   : uvicorn examples.03_fastapi_backend:app --reload")


if __name__ == "__main__":
    if not _FASTAPI_AVAILABLE:
        print(
            "WARNING: FastAPI is not installed. "
            "Install with: pip install fastapi uvicorn"
        )
    asyncio.run(main())
