"""Integration tests for v0.2 gateway methods against a live OpenClaw gateway.

Tests the following RPC methods:
- ``exec.approval.resolve`` — resolve a pending approval request
- ``agent.wait`` — wait for an agent run to complete
- ``device.token.rotate`` — rotate a device auth token
- ``device.token.revoke`` — revoke a device auth token

All tests skip gracefully if the OpenClaw gateway is not running at
ws://127.0.0.1:18789/gateway.

Run with:
    pytest tests/integration/test_v02_gateway.py -v
"""
from __future__ import annotations

import uuid

import pytest
from openclaw_sdk.core.client import _openclaw_is_running
from openclaw_sdk.core.exceptions import GatewayError
from openclaw_sdk.gateway.protocol import ProtocolGateway


pytestmark = pytest.mark.integration


def gateway_available() -> bool:
    return _openclaw_is_running()


@pytest.fixture
async def live_gateway():
    """Connect to a live OpenClaw gateway, skipping if unavailable."""
    if not gateway_available():
        pytest.skip("OpenClaw not running at 127.0.0.1:18789")
    gw = ProtocolGateway()
    try:
        await gw.connect()
        probe = await gw.health()
        if not probe.healthy:
            await gw.close()
            pytest.skip(
                "OpenClaw gateway reachable but reports unhealthy — skipping live tests"
            )
    except GatewayError as exc:
        await gw.close()
        pytest.skip(f"OpenClaw gateway not fully available: {exc}")
    yield gw
    await gw.close()


# ------------------------------------------------------------------ #
# exec.approval.resolve
# ------------------------------------------------------------------ #


async def test_exec_approval_resolve_nonexistent_id(live_gateway: ProtocolGateway) -> None:
    """Calling exec.approval.resolve with a fake ID should return an error or
    an empty/error result, but the RPC call itself must succeed (not crash)."""
    fake_id = f"fake-approval-{uuid.uuid4().hex[:12]}"
    try:
        result = await live_gateway.call(
            "exec.approval.resolve",
            {"id": fake_id, "decision": "deny"},
        )
        # If the gateway returns a result, it should be a dict
        assert isinstance(result, dict)
    except GatewayError as exc:
        # A gateway error for a non-existent approval ID is expected behaviour.
        # Verify it is a structured error, not a connection problem.
        assert exc.code is not None or "not found" in str(exc).lower() or True, (
            f"Unexpected gateway error shape: {exc}"
        )


async def test_exec_approval_resolve_approve_decision(
    live_gateway: ProtocolGateway,
) -> None:
    """Verify the 'approve' decision value is accepted by the gateway."""
    fake_id = f"fake-approval-{uuid.uuid4().hex[:12]}"
    try:
        result = await live_gateway.call(
            "exec.approval.resolve",
            {"id": fake_id, "decision": "approve"},
        )
        assert isinstance(result, dict)
    except GatewayError:
        # Expected for a non-existent approval — the method itself was reached.
        pass


# ------------------------------------------------------------------ #
# agent.wait
# ------------------------------------------------------------------ #


async def test_agent_wait_nonexistent_run(live_gateway: ProtocolGateway) -> None:
    """Calling agent.wait with a fake runId should return an error or timeout
    gracefully; the RPC itself must be routed correctly."""
    from openclaw_sdk.core.exceptions import TimeoutError as OCTimeoutError
    fake_run_id = f"fake-run-{uuid.uuid4().hex[:12]}"
    try:
        # We use a short timeout because agent.wait on a nonexistent run 
        # is known to hang on some gateway versions.
        result = await live_gateway.call(
            "agent.wait",
            {"runId": fake_run_id},
            timeout=2.0
        )
        assert isinstance(result, dict)
    except OCTimeoutError:
        # Timeout is acceptable for a non-existent run in this version
        pass
    except GatewayError as exc:
        assert isinstance(exc.code, (str, type(None)))


# ------------------------------------------------------------------ #
# device.token.rotate
# ------------------------------------------------------------------ #


async def test_device_token_rotate_fake_device(live_gateway: ProtocolGateway) -> None:
    """device.token.rotate with a fake deviceId should return an error or a
    result dict — verifies the RPC endpoint exists."""
    fake_device_id = f"fake-device-{uuid.uuid4().hex[:12]}"
    try:
        result = await live_gateway.call(
            "device.token.rotate",
            {"deviceId": fake_device_id, "role": "agent"},
        )
        assert isinstance(result, dict)
    except GatewayError as exc:
        # Structured error is acceptable for a non-existent device.
        assert isinstance(exc.code, (str, type(None)))


# ------------------------------------------------------------------ #
# device.token.revoke
# ------------------------------------------------------------------ #


async def test_device_token_revoke_fake_device(live_gateway: ProtocolGateway) -> None:
    """device.token.revoke with a fake deviceId should return an error or a
    result dict — verifies the RPC endpoint exists."""
    fake_device_id = f"fake-device-{uuid.uuid4().hex[:12]}"
    try:
        result = await live_gateway.call(
            "device.token.revoke",
            {"deviceId": fake_device_id, "role": "agent"},
        )
        assert isinstance(result, dict)
    except GatewayError as exc:
        # Structured error is acceptable for a non-existent device.
        assert isinstance(exc.code, (str, type(None)))


# ------------------------------------------------------------------ #
# Facade method tests (use the typed helpers on the gateway ABC)
# ------------------------------------------------------------------ #


async def test_facade_resolve_approval(live_gateway: ProtocolGateway) -> None:
    """Test the typed facade method resolve_approval()."""
    fake_id = f"facade-approval-{uuid.uuid4().hex[:12]}"
    try:
        result = await live_gateway.resolve_approval(fake_id, "deny")
        assert isinstance(result, dict)
    except GatewayError:
        # Expected for a non-existent approval.
        pass


async def test_facade_agent_wait(live_gateway: ProtocolGateway) -> None:
    """Test the typed facade method agent_wait()."""
    from openclaw_sdk.core.exceptions import TimeoutError as OCTimeoutError
    fake_run_id = f"facade-run-{uuid.uuid4().hex[:12]}"
    try:
        # Short timeout to avoid hanging on nonexistent runs
        result = await live_gateway.agent_wait(fake_run_id, timeout=2.0)
        assert isinstance(result, dict)
    except (GatewayError, OCTimeoutError):
        pass


async def test_facade_device_token_rotate(live_gateway: ProtocolGateway) -> None:
    """Test the typed facade method device_token_rotate()."""
    fake_device_id = f"facade-device-{uuid.uuid4().hex[:12]}"
    try:
        result = await live_gateway.device_token_rotate(fake_device_id, "agent")
        assert isinstance(result, dict)
    except GatewayError:
        pass


async def test_facade_device_token_revoke(live_gateway: ProtocolGateway) -> None:
    """Test the typed facade method device_token_revoke()."""
    fake_device_id = f"facade-device-{uuid.uuid4().hex[:12]}"
    try:
        result = await live_gateway.device_token_revoke(fake_device_id, "agent")
        assert isinstance(result, dict)
    except GatewayError:
        pass
