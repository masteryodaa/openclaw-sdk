"""Health check endpoint."""

from __future__ import annotations

import logging

from fastapi import APIRouter

from app.helpers import gateway

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health():
    """Check gateway + database health."""
    log.debug("GET /api/health")
    gw_ok = False
    try:
        client = await gateway.get_client()
        h = await client.health()
        gw_ok = h.healthy
    except Exception as exc:
        log.warning("Health check — gateway error: %s", exc)

    status = "ok" if gw_ok else "degraded"
    log.info("Health: status=%s gateway=%s", status, gw_ok)
    return {"status": status, "gateway": gw_ok}
