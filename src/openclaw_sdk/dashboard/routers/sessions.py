"""Session management endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from openclaw_sdk.core.exceptions import OpenClawError

router = APIRouter(tags=["sessions"])


@router.get("/api/sessions/{key:path}/preview")
async def session_preview(key: str, request: Request) -> JSONResponse:
    """Preview a session.  Uses ``{keys: [key]}`` per verified protocol."""
    client = request.app.state.client
    try:
        result = await client.gateway.call("sessions.preview", {"keys": [key]})
    except OpenClawError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse(content=result)


@router.post("/api/sessions/{key:path}/reset")
async def session_reset(key: str, request: Request) -> JSONResponse:
    """Reset a session's conversation history.  Uses ``{key}``."""
    client = request.app.state.client
    try:
        result = await client.gateway.call("sessions.reset", {"key": key})
    except OpenClawError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse(content=result)


@router.delete("/api/sessions/{key:path}")
async def session_delete(key: str, request: Request) -> JSONResponse:
    """Delete a session permanently.  Uses ``{key}``."""
    client = request.app.state.client
    try:
        result = await client.gateway.call("sessions.delete", {"key": key})
    except OpenClawError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse(content=result)
