"""ClawForge -- AI App Builder powered by OpenClaw SDK.

Run:
    python main.py                          # starts on http://127.0.0.1:8200
    uvicorn main:app --reload --port 8200   # dev mode
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.helpers import database, gateway
from app.routers.billing import router as billing_router
from app.routers.build import router as build_router
from app.routers.chat import router as chat_router
from app.routers.export import router as export_router
from app.routers.files import router as files_router
from app.routers.health import router as health_router
from app.routers.projects import router as projects_router
from app.routers.templates import router as templates_router
from app.routers.workspace_site import router as workspace_site_router

# ---------------------------------------------------------------------------
# Logging setup — all backend modules use logging.getLogger(__name__)
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
# Quiet noisy third-party loggers
logging.getLogger("websockets").setLevel(logging.WARNING)
logging.getLogger("aiosqlite").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.INFO)

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Initialising database...")
    await database.init_db()
    log.info("Database ready")
    try:
        await gateway.connect()
        log.info("Connected to OpenClaw at %s", gateway.GATEWAY_URL)
    except Exception as exc:
        log.warning("Gateway unavailable: %s", exc)
        log.warning("Start OpenClaw -- the app will connect on first request.")
    yield
    log.info("Shutting down — disconnecting gateway")
    await gateway.disconnect()
    log.info("Shutdown complete")


app = FastAPI(title="ClawForge", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(projects_router)
app.include_router(chat_router)
app.include_router(build_router)
app.include_router(files_router)
app.include_router(templates_router)
app.include_router(billing_router)
app.include_router(export_router)
# Workspace static file server — MUST be last (catch-all path pattern)
app.include_router(workspace_site_router)

if __name__ == "__main__":
    import uvicorn

    print()
    print("=" * 50)
    print("  ClawForge -- AI App Builder")
    print("  http://127.0.0.1:8200")
    print("=" * 50)
    print()
    uvicorn.run(app, host="127.0.0.1", port=8200, log_level="info")
