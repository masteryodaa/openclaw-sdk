"""Health & system endpoints."""

from __future__ import annotations

import json

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from . import gateway

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health")
async def health():
    """Gateway health check."""
    try:
        client = await gateway.get_client()
        status = await client.health()
        return {
            "healthy": status.healthy,
            "latency_ms": round(status.latency_ms or 0),
            "version": status.version,
            "gateway_url": gateway.GATEWAY_URL,
        }
    except Exception as exc:
        gateway.reset()
        return JSONResponse(status_code=503, content={
            "healthy": False,
            "gateway_url": gateway.GATEWAY_URL,
            "error": str(exc),
        })
