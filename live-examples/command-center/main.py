"""OpenClaw Command Center — entry point.

Run:
    python main.py                     # starts on http://127.0.0.1:8080
    uvicorn main:app --reload --port 8080  # dev mode with hot-reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app import gateway
from app.routes_agents import router as agents_router
from app.routes_audit import router as audit_router
from app.routes_autonomous import router as autonomous_router
from app.routes_billing import router as billing_router
from app.routes_channels import router as channels_router
from app.routes_chat import router as chat_router
from app.routes_config import router as config_router
from app.routes_connectors import router as connectors_router
from app.routes_files import router as files_router
from app.routes_guardrails import router as guardrails_router
from app.routes_health import router as health_router
from app.routes_models import router as models_router
from app.routes_observe import router as observe_router
from app.routes_ops import router as ops_router
from app.routes_pipelines import router as pipelines_router
from app.routes_schedules import router as schedules_router
from app.routes_sessions import router as sessions_router
from app.routes_templates import router as templates_router
from app.routes_webhooks import router as webhooks_router
from app.routes_workflows import router as workflows_router

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await gateway.connect()
        print(f"[OK] Connected to OpenClaw at {gateway.GATEWAY_URL}")
    except Exception as exc:
        print(f"[WARN] Gateway unavailable: {exc}")
        print("       Start OpenClaw — the app will connect on first request.")
    yield
    await gateway.disconnect()


app = FastAPI(title="OpenClaw Command Center", version="2.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# API routes
app.include_router(health_router)
app.include_router(agents_router)
app.include_router(chat_router)
app.include_router(config_router)
app.include_router(sessions_router)
app.include_router(channels_router)
app.include_router(schedules_router)
app.include_router(models_router)
app.include_router(pipelines_router)
app.include_router(observe_router)
app.include_router(guardrails_router)
app.include_router(ops_router)
app.include_router(audit_router)
app.include_router(billing_router)
app.include_router(connectors_router)
app.include_router(files_router)
app.include_router(templates_router)
app.include_router(workflows_router)
app.include_router(webhooks_router)
app.include_router(autonomous_router)


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse((STATIC_DIR / "index.html").read_text(encoding="utf-8"))


if __name__ == "__main__":
    import uvicorn

    print()
    print("=" * 50)
    print("  OpenClaw Command Center v2.0")
    print("  http://127.0.0.1:8080")
    print("=" * 50)
    print()
    uvicorn.run(app, host="127.0.0.1", port=8080, log_level="info")
