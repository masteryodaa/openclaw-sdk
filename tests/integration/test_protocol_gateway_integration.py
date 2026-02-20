"""Integration tests requiring a live OpenClaw gateway.

Run with:
    pytest tests/integration/ -m integration

These tests are skipped if OpenClaw is not running at ws://127.0.0.1:18789/gateway.
"""
from __future__ import annotations

import pytest
from openclaw_sdk.core.client import _openclaw_is_running
from openclaw_sdk.core.exceptions import GatewayError
from openclaw_sdk.gateway.protocol import ProtocolGateway


pytestmark = pytest.mark.integration


def gateway_available() -> bool:
    return _openclaw_is_running()


@pytest.fixture
async def live_gateway():
    if not gateway_available():
        pytest.skip("OpenClaw not running at 127.0.0.1:18789")
    gw = ProtocolGateway()
    try:
        await gw.connect()
        # Probe the gateway before yielding; skip if the connection is not
        # fully functional (e.g. auth token missing or gateway unhealthy).
        probe = await gw.health()
        if not probe.healthy:
            await gw.close()
            pytest.skip("OpenClaw gateway reachable but reports unhealthy — skipping live tests")
    except GatewayError as exc:
        await gw.close()
        pytest.skip(f"OpenClaw gateway not fully available: {exc}")
    yield gw
    await gw.close()


async def test_health_live(live_gateway):
    status = await live_gateway.health()
    assert status.healthy


async def test_sessions_list_live(live_gateway):
    result = await live_gateway.call("sessions.list", {})
    assert "sessions" in result


async def test_channel_status_live(live_gateway):
    result = await live_gateway.call("channels.status", {})
    assert "channels" in result
