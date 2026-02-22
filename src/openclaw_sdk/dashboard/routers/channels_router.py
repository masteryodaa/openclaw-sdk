"""Channel status endpoint."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from openclaw_sdk.core.exceptions import OpenClawError

router = APIRouter(tags=["channels"])


@router.get("/api/channels/status")
async def channel_status(request: Request) -> JSONResponse:
    """Get all channel statuses."""
    client = request.app.state.client
    try:
        result = await client.channels.status()
    except OpenClawError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse(content=result)
