"""Health check endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(tags=["health"])


@router.get("/api/health")
async def health_check(request: Request) -> JSONResponse:
    """Check gateway health status."""
    client = request.app.state.client
    status = await client.gateway.health()
    return JSONResponse(content={
        "healthy": status.healthy,
        "latency_ms": status.latency_ms,
        "version": status.version,
        "details": status.details,
    })
