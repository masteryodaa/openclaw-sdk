"""Config management endpoints."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from openclaw_sdk.core.exceptions import OpenClawError

router = APIRouter(tags=["config"])


class _ConfigSetBody(BaseModel):
    raw: str


class _ConfigPatchBody(BaseModel):
    raw: str
    base_hash: str | None = None


@router.get("/api/config")
async def get_config(request: Request) -> JSONResponse:
    """Get the current runtime configuration via ``config.get``."""
    client = request.app.state.client
    try:
        result = await client.gateway.call("config.get", {})
    except OpenClawError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse(content=result)


@router.put("/api/config")
async def set_config(body: _ConfigSetBody, request: Request) -> JSONResponse:
    """Replace the entire config via ``config.set`` with ``{raw}``."""
    client = request.app.state.client
    try:
        result = await client.gateway.call("config.set", {"raw": body.raw})
    except OpenClawError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse(content=result)


@router.patch("/api/config")
async def patch_config(body: _ConfigPatchBody, request: Request) -> JSONResponse:
    """Patch the config via ``config.patch`` with ``{raw, baseHash?}``."""
    client = request.app.state.client
    params: dict[str, Any] = {"raw": body.raw}
    if body.base_hash is not None:
        params["baseHash"] = body.base_hash
    try:
        result = await client.gateway.call("config.patch", params)
    except OpenClawError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse(content=result)
