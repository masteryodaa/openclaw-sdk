"""Webhook management endpoints."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

router = APIRouter(tags=["webhooks"])


class _WebhookRegisterBody(BaseModel):
    name: str
    url: str
    events: list[str] = Field(default_factory=list)
    secret: str | None = None


class _WebhookFireBody(BaseModel):
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)


@router.get("/api/webhooks")
async def list_webhooks(request: Request) -> JSONResponse:
    """List all registered webhooks."""
    wm = request.app.state.webhook_manager
    if wm is None:
        raise HTTPException(status_code=404, detail="WebhookManager not configured")
    hooks = wm.list_webhooks()
    return JSONResponse(content=[h.model_dump() for h in hooks])


@router.post("/api/webhooks")
async def register_webhook(body: _WebhookRegisterBody, request: Request) -> JSONResponse:
    """Register a new webhook."""
    wm = request.app.state.webhook_manager
    if wm is None:
        raise HTTPException(status_code=404, detail="WebhookManager not configured")
    from openclaw_sdk.webhooks.manager import WebhookConfig

    config = WebhookConfig(
        name=body.name,
        url=body.url,
        events=body.events,
        secret=body.secret,
    )
    try:
        result = wm.register(config)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return JSONResponse(content=result.model_dump(), status_code=201)


@router.delete("/api/webhooks/{name}")
async def unregister_webhook(name: str, request: Request) -> JSONResponse:
    """Unregister a webhook by name."""
    wm = request.app.state.webhook_manager
    if wm is None:
        raise HTTPException(status_code=404, detail="WebhookManager not configured")
    removed = wm.unregister(name)
    if not removed:
        raise HTTPException(status_code=404, detail=f"Webhook '{name}' not found")
    return JSONResponse(content={"removed": True})


@router.post("/api/webhooks/fire")
async def fire_webhook(body: _WebhookFireBody, request: Request) -> JSONResponse:
    """Fire a test event to all matching webhooks."""
    wm = request.app.state.webhook_manager
    if wm is None:
        raise HTTPException(status_code=404, detail="WebhookManager not configured")
    deliveries = await wm.fire(body.event_type, body.payload)
    return JSONResponse(content=[d.model_dump(mode="json") for d in deliveries])
