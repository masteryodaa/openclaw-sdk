"""Configuration management endpoints."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from . import gateway

router = APIRouter(prefix="/api/config", tags=["config"])


class ConfigSetBody(BaseModel):
    config: dict


class ConfigPatchBody(BaseModel):
    config: dict
    base_hash: str | None = None


@router.get("")
async def get_config():
    """Fetch current OpenClaw runtime configuration."""
    client = await gateway.get_client()
    result = await client.config_mgr.get()
    raw = result.get("raw", "{}")
    parsed = json.loads(raw) if isinstance(raw, str) else raw
    return {"config": parsed, "hash": result.get("hash")}


@router.get("/schema")
async def get_schema():
    """Fetch the JSON Schema for runtime configuration."""
    client = await gateway.get_client()
    return await client.config_mgr.schema()


@router.put("")
async def set_config(body: ConfigSetBody):
    """Replace the entire runtime configuration."""
    client = await gateway.get_client()
    raw = json.dumps(body.config)
    result = await client.config_mgr.set(raw)
    return {"success": True, "result": result}


@router.patch("")
async def patch_config(body: ConfigPatchBody):
    """Patch runtime configuration with compare-and-swap."""
    client = await gateway.get_client()
    raw = json.dumps(body.config)
    result = await client.config_mgr.patch(raw, base_hash=body.base_hash)
    return {"success": True, "result": result}
