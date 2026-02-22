"""Health check endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from app.helpers import gateway

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health():
    """Check gateway + database health."""
    gw_ok = False
    try:
        client = await gateway.get_client()
        h = await client.health()
        gw_ok = h.healthy
    except Exception:
        pass

    return {"status": "ok" if gw_ok else "degraded", "gateway": gw_ok}
