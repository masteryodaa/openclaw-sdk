"""Channel management endpoints (WhatsApp, Telegram, etc.)."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from . import gateway

router = APIRouter(prefix="/api/channels", tags=["channels"])


class PairingCodeBody(BaseModel):
    phone: str | None = None


@router.get("")
async def channel_status():
    """Get status of all configured channels."""
    client = await gateway.get_client()
    return await client.channels.status()


@router.post("/{channel}/login")
async def start_login(channel: str):
    """Start web-based QR login flow.

    The gateway's ``web.login.start`` takes no channel param
    (auto-selects the configured web-login channel).
    The ``{channel}`` path param is kept for UI routing consistency.
    """
    client = await gateway.get_client()
    return await client.channels.web_login_start()


@router.post("/{channel}/login/wait")
async def wait_login(channel: str, timeout_ms: int = 120000):
    """Wait for QR scan completion."""
    client = await gateway.get_client()
    return await client.channels.web_login_wait(timeout_ms=timeout_ms)


@router.post("/{channel}/pairing-code")
async def pairing_code(channel: str, body: PairingCodeBody):
    """Request numeric pairing code instead of QR."""
    client = await gateway.get_client()
    return await client.channels.request_pairing_code(phone=body.phone)


@router.post("/{channel}/logout")
async def logout_channel(channel: str):
    """Log out of a channel."""
    client = await gateway.get_client()
    result = await client.channels.logout(channel)
    return {"success": result}
