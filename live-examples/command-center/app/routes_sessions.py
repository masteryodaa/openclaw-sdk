"""Session management endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from . import gateway

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class SessionPatchBody(BaseModel):
    patch: dict


@router.get("")
async def list_sessions():
    """List all active sessions."""
    client = await gateway.get_client()
    result = await client.gateway.sessions_list()
    return {"sessions": result}


@router.get("/{key:path}/preview")
async def preview_session(key: str):
    """Preview a session's conversation."""
    client = await gateway.get_client()
    result = await client.gateway.sessions_preview([key])
    return result


@router.get("/{key:path}/resolve")
async def resolve_session(key: str):
    """Resolve session key to full descriptor."""
    client = await gateway.get_client()
    return await client.gateway.sessions_resolve(key)


@router.post("/{key:path}/reset")
async def reset_session(key: str):
    """Reset session conversation history."""
    client = await gateway.get_client()
    result = await client.gateway.sessions_reset(key)
    return {"success": True, "result": result}


@router.post("/{key:path}/compact")
async def compact_session(key: str):
    """Compact session (summarize history to reduce tokens)."""
    client = await gateway.get_client()
    result = await client.gateway.sessions_compact(key)
    return {"success": True, "result": result}


@router.delete("/{key:path}")
async def delete_session(key: str):
    """Delete session permanently."""
    client = await gateway.get_client()
    result = await client.gateway.sessions_delete(key)
    return {"success": True, "result": result}


@router.patch("/{key:path}")
async def patch_session(key: str, body: SessionPatchBody):
    """Apply partial update to session."""
    client = await gateway.get_client()
    result = await client.gateway.sessions_patch(key, body.patch)
    return {"success": True, "result": result}
