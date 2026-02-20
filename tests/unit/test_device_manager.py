"""Tests for DeviceManager (device.token.rotate, device.token.revoke)."""

from __future__ import annotations

from openclaw_sdk.core.client import OpenClawClient
from openclaw_sdk.core.config import ClientConfig
from openclaw_sdk.devices.manager import DeviceManager
from openclaw_sdk.gateway.mock import MockGateway


def _make_manager() -> tuple[MockGateway, DeviceManager]:
    mock = MockGateway()
    mock._connected = True
    return mock, DeviceManager(mock)


def _make_client() -> tuple[MockGateway, OpenClawClient]:
    mock = MockGateway()
    mock._connected = True
    return mock, OpenClawClient(config=ClientConfig(), gateway=mock)


# ------------------------------------------------------------------ #
# DeviceManager.rotate_token
# ------------------------------------------------------------------ #


async def test_rotate_token_calls_gateway() -> None:
    mock, mgr = _make_manager()
    mock.register(
        "device.token.rotate",
        {"token": "new-token-abc", "expiresAt": "2026-03-01T00:00:00Z"},
    )

    result = await mgr.rotate_token("device_abc", "operator")

    mock.assert_called("device.token.rotate")
    assert result["token"] == "new-token-abc"


async def test_rotate_token_passes_correct_params() -> None:
    mock, mgr = _make_manager()
    mock.register("device.token.rotate", {"token": "rotated"})

    await mgr.rotate_token("device_abc", "operator")

    _, params = mock.calls[-1]
    assert params["deviceId"] == "device_abc"
    assert params["role"] == "operator"


# ------------------------------------------------------------------ #
# DeviceManager.revoke_token
# ------------------------------------------------------------------ #


async def test_revoke_token_calls_gateway() -> None:
    mock, mgr = _make_manager()
    mock.register("device.token.revoke", {"revoked": True})

    result = await mgr.revoke_token("device_abc", "node")

    mock.assert_called("device.token.revoke")
    assert result["revoked"] is True


async def test_revoke_token_passes_correct_params() -> None:
    mock, mgr = _make_manager()
    mock.register("device.token.revoke", {"revoked": True})

    await mgr.revoke_token("device_abc", "node")

    _, params = mock.calls[-1]
    assert params["deviceId"] == "device_abc"
    assert params["role"] == "node"


# ------------------------------------------------------------------ #
# Client property
# ------------------------------------------------------------------ #


async def test_client_devices_property_returns_device_manager() -> None:
    _, client = _make_client()
    assert isinstance(client.devices, DeviceManager)


async def test_client_devices_property_is_lazy_singleton() -> None:
    _, client = _make_client()
    assert client.devices is client.devices


async def test_client_devices_rotate_token() -> None:
    mock, client = _make_client()
    mock.register("device.token.rotate", {"token": "via-client"})

    result = await client.devices.rotate_token("dev-1", "operator")

    mock.assert_called("device.token.rotate")
    assert result["token"] == "via-client"


async def test_client_devices_revoke_token() -> None:
    mock, client = _make_client()
    mock.register("device.token.revoke", {"revoked": True})

    result = await client.devices.revoke_token("dev-1", "node")

    mock.assert_called("device.token.revoke")
    assert result["revoked"] is True
