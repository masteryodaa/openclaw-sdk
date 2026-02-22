"""ClawForge -- AI App Builder powered by OpenClaw SDK.

Run:
    python main.py                          # starts on http://127.0.0.1:8200
    uvicorn main:app --reload --port 8200   # dev mode
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.helpers import database, gateway
from app.routers.health import router as health_router
from app.routers.projects import router as projects_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.init_db()
    try:
        await gateway.connect()
        print(f"[OK] Connected to OpenClaw at {gateway.GATEWAY_URL}")
    except Exception as exc:
        print(f"[WARN] Gateway unavailable: {exc}")
        print("       Start OpenClaw -- the app will connect on first request.")
    yield
    await gateway.disconnect()


app = FastAPI(title="ClawForge", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(projects_router)

if __name__ == "__main__":
    import uvicorn

    print()
    print("=" * 50)
    print("  ClawForge -- AI App Builder")
    print("  http://127.0.0.1:8200")
    print("=" * 50)
    print()
    uvicorn.run(app, host="127.0.0.1", port=8200, log_level="info")
