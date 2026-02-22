"""Gateway connection manager — single shared OpenClawClient."""

from __future__ import annotations

import asyncio

from openclaw_sdk import GatewayError, OpenClawClient

GATEWAY_URL = "ws://127.0.0.1:18789/gateway"
CONNECT_TIMEOUT = 5.0

_client: OpenClawClient | None = None


async def _fresh_connect() -> OpenClawClient:
    """Create a brand-new gateway connection."""
    return await asyncio.wait_for(
        OpenClawClient.connect(gateway_ws_url=GATEWAY_URL),
        timeout=CONNECT_TIMEOUT,
    )


async def connect() -> OpenClawClient:
    """Connect to the gateway (or return cached client)."""
    global _client
    if _client is not None:
        return _client
    _client = await _fresh_connect()
    return _client


async def get_client() -> OpenClawClient:
    """Get connected client; reconnects automatically if stale."""
    global _client
    if _client is not None:
        try:
            h = await asyncio.wait_for(_client.health(), timeout=2.0)
            if not h.healthy:
                raise ConnectionError("gateway unhealthy")
            return _client
        except Exception:
            try:
                await _client.close()
            except Exception:
                pass
            _client = None

    for attempt in range(2):
        try:
            _client = await _fresh_connect()
            return _client
        except Exception:
            if attempt == 0:
                await asyncio.sleep(2.0)
    raise GatewayError(f"Cannot reach gateway at {GATEWAY_URL}")


async def disconnect() -> None:
    """Close the gateway connection."""
    global _client
    if _client is not None:
        await _client.close()
        _client = None


def reset() -> None:
    """Reset client reference (for reconnection on next request)."""
    global _client
    _client = None
