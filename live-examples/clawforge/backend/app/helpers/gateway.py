"""Gateway connection manager — single shared OpenClawClient."""

from __future__ import annotations

import asyncio
import logging

from openclaw_sdk import GatewayError, OpenClawClient

log = logging.getLogger(__name__)

GATEWAY_URL = "ws://127.0.0.1:18789/gateway"
CONNECT_TIMEOUT = 5.0

_client: OpenClawClient | None = None


async def _fresh_connect() -> OpenClawClient:
    """Create a brand-new gateway connection."""
    log.info("Opening fresh gateway connection to %s", GATEWAY_URL)
    client = await asyncio.wait_for(
        OpenClawClient.connect(gateway_ws_url=GATEWAY_URL),
        timeout=CONNECT_TIMEOUT,
    )
    log.info("Gateway connection established")
    return client


async def connect() -> OpenClawClient:
    """Connect to the gateway (or return cached client)."""
    global _client
    if _client is not None:
        log.debug("Returning cached gateway client")
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
                log.warning("Gateway health check failed (unhealthy)")
                raise ConnectionError("gateway unhealthy")
            log.debug("Gateway health OK")
            return _client
        except Exception as exc:
            log.warning("Gateway stale, reconnecting: %s", exc)
            try:
                await _client.close()
            except Exception:
                pass
            _client = None

    for attempt in range(2):
        try:
            log.info("Gateway connect attempt %d/2", attempt + 1)
            _client = await _fresh_connect()
            return _client
        except Exception as exc:
            log.error("Connect attempt %d failed: %s", attempt + 1, exc)
            if attempt == 0:
                await asyncio.sleep(2.0)
    raise GatewayError(f"Cannot reach gateway at {GATEWAY_URL}")


async def disconnect() -> None:
    """Close the gateway connection."""
    global _client
    if _client is not None:
        log.info("Disconnecting gateway client")
        await _client.close()
        _client = None
        log.info("Gateway disconnected")


def reset() -> None:
    """Reset client reference (for reconnection on next request)."""
    global _client
    log.warning("Gateway client reset — will reconnect on next request")
    _client = None
