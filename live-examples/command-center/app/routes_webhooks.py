"""Webhook management endpoints — register, list, deliver, and test webhooks."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from openclaw_sdk.webhooks.manager import WebhookConfig, WebhookManager

from . import gateway

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

# Shared singleton instance (per-server lifetime)
_webhook_mgr = WebhookManager()


# -- Request models --


class RegisterWebhookBody(BaseModel):
    name: str
    url: str
    events: list[str] = []
    secret: str | None = None
    enabled: bool = True
    max_retries: int = 3


class TestWebhookBody(BaseModel):
    event_type: str = "test.ping"
    payload: dict = {}


# -- Endpoints --


@router.post("")
async def register_webhook(body: RegisterWebhookBody):
    """Register a new webhook endpoint."""
    try:
        config = WebhookConfig(
            name=body.name,
            url=body.url,
            events=body.events,
            secret=body.secret,
            enabled=body.enabled,
            max_retries=body.max_retries,
        )
        _webhook_mgr.register(config)
        return {
            "registered": True,
            "name": config.name,
            "url": config.url,
            "events": config.events,
        }
    except ValueError as exc:
        return {"error": str(exc)}


@router.get("")
async def list_webhooks():
    """List all registered webhooks."""
    webhooks = _webhook_mgr.list_webhooks()
    return {
        "webhooks": [
            {
                "name": w.name,
                "url": w.url,
                "events": w.events,
                "enabled": w.enabled,
                "max_retries": w.max_retries,
                "secret_set": w.secret is not None,
            }
            for w in webhooks
        ]
    }


@router.delete("/{webhook_name}")
async def unregister_webhook(webhook_name: str):
    """Unregister a webhook by name."""
    removed = _webhook_mgr.unregister(webhook_name)
    return {"removed": removed, "name": webhook_name}


@router.get("/deliveries")
async def list_deliveries(webhook_name: str | None = None, limit: int = 50):
    """List webhook delivery history."""
    deliveries = _webhook_mgr.get_deliveries(
        webhook_name=webhook_name,
        limit=limit,
    )
    return {
        "deliveries": [
            {
                "delivery_id": d.delivery_id,
                "webhook_name": d.webhook_name,
                "event_type": d.event_type,
                "status": d.status,
                "attempts": d.attempts,
                "max_attempts": d.max_attempts,
                "response_status": d.response_status,
                "error": d.error,
                "created_at": d.created_at.isoformat(),
                "last_attempt_at": d.last_attempt_at.isoformat() if d.last_attempt_at else None,
            }
            for d in deliveries
        ]
    }


@router.post("/{webhook_name}/test")
async def test_webhook(webhook_name: str, body: TestWebhookBody | None = None):
    """Fire a test event to a specific webhook."""
    config = _webhook_mgr.get(webhook_name)
    if config is None:
        return {"error": f"Webhook '{webhook_name}' not found"}

    event_type = body.event_type if body else "test.ping"
    payload = body.payload if body else {"message": "Test ping from Command Center"}

    # Deliver directly to bypass event filter (test should always reach the webhook)
    d = await _webhook_mgr._engine.deliver(config, event_type, payload)
    _webhook_mgr._deliveries.append(d)
    return {
        "delivered": d.status == "success",
        "delivery_id": d.delivery_id,
        "status": d.status,
        "attempts": d.attempts,
        "response_status": d.response_status,
        "error": d.error,
    }
