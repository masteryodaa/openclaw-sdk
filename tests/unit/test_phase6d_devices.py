"""Phase 6D — Device pairing gateway methods (4 methods).

Tests cover:
- All 4 gateway facade methods (correct RPC method names, params)
- All 4 DeviceManager methods
- Backward compatibility with existing rotate_token / revoke_token
- Response structure validation (pending/paired arrays)
"""

from __future__ import annotations

from typing import Any

from openclaw_sdk.core.client import OpenClawClient
from openclaw_sdk.core.config import ClientConfig
from openclaw_sdk.devices.manager import DeviceManager
from openclaw_sdk.gateway.mock import MockGateway

# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #


def _make_manager() -> tuple[MockGateway, DeviceManager]:
    mock = MockGateway()
    mock._connected = True
    return mock, DeviceManager(mock)


def _make_client() -> tuple[MockGateway, OpenClawClient]:
    mock = MockGateway()
    mock._connected = True
    return mock, OpenClawClient(config=ClientConfig(), gateway=mock)


_PAIR_LIST_RESPONSE: dict[str, Any] = {
    "pending": [
        {
            "requestId": "req_001",
            "platform": "linux",
            "clientId": "cli-abc",
            "clientMode": "cli",
            "createdAtMs": 1709100000000,
        },
    ],
    "paired": [
        {
            "deviceId": "dev_001",
            "publicKey": "ed25519:abc123",
            "platform": "darwin",
            "clientId": "web-xyz",
            "clientMode": "web",
            "role": "operator",
            "roles": ["operator"],
            "scopes": ["chat", "config"],
            "createdAtMs": 1709000000000,
            "approvedAtMs": 1709000100000,
            "tokens": [
                {
                    "role": "operator",
                    "scopes": ["chat", "config"],
                    "createdAtMs": 1709000100000,
                    "lastUsedAtMs": 1709100000000,
                },
            ],
        },
    ],
}


# ================================================================== #
# Gateway facade tests
# ================================================================== #


class TestGatewayDevicePairList:
    async def test_calls_correct_method(self) -> None:
        mock = MockGateway()
        mock._connected = True
        mock.register("device.pair.list", _PAIR_LIST_RESPONSE)

        result = await mock.device_pair_list()

        mock.assert_called("device.pair.list")
        assert "pending" in result
        assert "paired" in result

    async def test_passes_empty_params(self) -> None:
        mock = MockGateway()
        mock._connected = True
        mock.register("device.pair.list", _PAIR_LIST_RESPONSE)

        await mock.device_pair_list()

        _, params = mock.calls[-1]
        assert params == {}

    async def test_response_structure(self) -> None:
        mock = MockGateway()
        mock._connected = True
        mock.register("device.pair.list", _PAIR_LIST_RESPONSE)

        result = await mock.device_pair_list()

        assert isinstance(result["pending"], list)
        assert isinstance(result["paired"], list)
        assert len(result["pending"]) == 1
        assert len(result["paired"]) == 1
        paired_device = result["paired"][0]
        assert paired_device["deviceId"] == "dev_001"
        assert paired_device["publicKey"] == "ed25519:abc123"
        assert "tokens" in paired_device
        assert paired_device["tokens"][0]["role"] == "operator"


class TestGatewayDevicePairApprove:
    async def test_calls_correct_method(self) -> None:
        mock = MockGateway()
        mock._connected = True
        mock.register("device.pair.approve", {"ok": True})

        result = await mock.device_pair_approve("req_001")

        mock.assert_called("device.pair.approve")
        assert result["ok"] is True

    async def test_passes_request_id(self) -> None:
        mock = MockGateway()
        mock._connected = True
        mock.register("device.pair.approve", {"ok": True})

        await mock.device_pair_approve("req_001")

        _, params = mock.calls[-1]
        assert params == {"requestId": "req_001"}


class TestGatewayDevicePairReject:
    async def test_calls_correct_method(self) -> None:
        mock = MockGateway()
        mock._connected = True
        mock.register("device.pair.reject", {"ok": True})

        result = await mock.device_pair_reject("req_002")

        mock.assert_called("device.pair.reject")
        assert result["ok"] is True

    async def test_passes_request_id(self) -> None:
        mock = MockGateway()
        mock._connected = True
        mock.register("device.pair.reject", {"ok": True})

        await mock.device_pair_reject("req_002")

        _, params = mock.calls[-1]
        assert params == {"requestId": "req_002"}


class TestGatewayDevicePairRemove:
    async def test_calls_correct_method(self) -> None:
        mock = MockGateway()
        mock._connected = True
        mock.register("device.pair.remove", {"ok": True})

        result = await mock.device_pair_remove("dev_001")

        mock.assert_called("device.pair.remove")
        assert result["ok"] is True

    async def test_passes_device_id(self) -> None:
        mock = MockGateway()
        mock._connected = True
        mock.register("device.pair.remove", {"ok": True})

        await mock.device_pair_remove("dev_001")

        _, params = mock.calls[-1]
        assert params == {"deviceId": "dev_001"}


# ================================================================== #
# DeviceManager tests
# ================================================================== #


class TestDeviceManagerListPaired:
    async def test_calls_gateway(self) -> None:
        mock, mgr = _make_manager()
        mock.register("device.pair.list", _PAIR_LIST_RESPONSE)

        result = await mgr.list_paired()

        mock.assert_called("device.pair.list")
        assert "pending" in result
        assert "paired" in result

    async def test_passes_empty_params(self) -> None:
        mock, mgr = _make_manager()
        mock.register("device.pair.list", _PAIR_LIST_RESPONSE)

        await mgr.list_paired()

        _, params = mock.calls[-1]
        assert params == {}

    async def test_pending_array_contents(self) -> None:
        mock, mgr = _make_manager()
        mock.register("device.pair.list", _PAIR_LIST_RESPONSE)

        result = await mgr.list_paired()

        pending = result["pending"]
        assert len(pending) == 1
        assert pending[0]["requestId"] == "req_001"
        assert pending[0]["platform"] == "linux"

    async def test_paired_array_contents(self) -> None:
        mock, mgr = _make_manager()
        mock.register("device.pair.list", _PAIR_LIST_RESPONSE)

        result = await mgr.list_paired()

        paired = result["paired"]
        assert len(paired) == 1
        device = paired[0]
        assert device["deviceId"] == "dev_001"
        assert device["role"] == "operator"
        assert device["roles"] == ["operator"]
        assert device["scopes"] == ["chat", "config"]

    async def test_empty_response(self) -> None:
        mock, mgr = _make_manager()
        mock.register("device.pair.list", {"pending": [], "paired": []})

        result = await mgr.list_paired()

        assert result["pending"] == []
        assert result["paired"] == []


class TestDeviceManagerApprovePairing:
    async def test_calls_gateway(self) -> None:
        mock, mgr = _make_manager()
        mock.register("device.pair.approve", {"ok": True})

        result = await mgr.approve_pairing("req_001")

        mock.assert_called("device.pair.approve")
        assert result["ok"] is True

    async def test_passes_correct_params(self) -> None:
        mock, mgr = _make_manager()
        mock.register("device.pair.approve", {"ok": True})

        await mgr.approve_pairing("req_xyz")

        _, params = mock.calls[-1]
        assert params == {"requestId": "req_xyz"}


class TestDeviceManagerRejectPairing:
    async def test_calls_gateway(self) -> None:
        mock, mgr = _make_manager()
        mock.register("device.pair.reject", {"ok": True})

        result = await mgr.reject_pairing("req_002")

        mock.assert_called("device.pair.reject")
        assert result["ok"] is True

    async def test_passes_correct_params(self) -> None:
        mock, mgr = _make_manager()
        mock.register("device.pair.reject", {"ok": True})

        await mgr.reject_pairing("req_abc")

        _, params = mock.calls[-1]
        assert params == {"requestId": "req_abc"}


class TestDeviceManagerRemoveDevice:
    async def test_calls_gateway(self) -> None:
        mock, mgr = _make_manager()
        mock.register("device.pair.remove", {"ok": True})

        result = await mgr.remove_device("dev_001")

        mock.assert_called("device.pair.remove")
        assert result["ok"] is True

    async def test_passes_correct_params(self) -> None:
        mock, mgr = _make_manager()
        mock.register("device.pair.remove", {"ok": True})

        await mgr.remove_device("dev_abc")

        _, params = mock.calls[-1]
        assert params == {"deviceId": "dev_abc"}


# ================================================================== #
# Backward compatibility — existing methods still work
# ================================================================== #


class TestBackwardCompatibility:
    async def test_rotate_token_still_works(self) -> None:
        mock, mgr = _make_manager()
        mock.register("device.token.rotate", {"token": "new-token"})

        result = await mgr.rotate_token("device_abc", "operator")

        mock.assert_called("device.token.rotate")
        assert result["token"] == "new-token"
        _, params = mock.calls[-1]
        assert params == {"deviceId": "device_abc", "role": "operator"}

    async def test_revoke_token_still_works(self) -> None:
        mock, mgr = _make_manager()
        mock.register("device.token.revoke", {"revoked": True})

        result = await mgr.revoke_token("device_abc", "node")

        mock.assert_called("device.token.revoke")
        assert result["revoked"] is True
        _, params = mock.calls[-1]
        assert params == {"deviceId": "device_abc", "role": "node"}

    async def test_gateway_device_token_rotate_facade(self) -> None:
        mock = MockGateway()
        mock._connected = True
        mock.register("device.token.rotate", {"token": "rotated"})

        result = await mock.device_token_rotate("dev-1", "operator")

        mock.assert_called("device.token.rotate")
        assert result["token"] == "rotated"

    async def test_gateway_device_token_revoke_facade(self) -> None:
        mock = MockGateway()
        mock._connected = True
        mock.register("device.token.revoke", {"revoked": True})

        result = await mock.device_token_revoke("dev-1", "node")

        mock.assert_called("device.token.revoke")
        assert result["revoked"] is True


# ================================================================== #
# Client integration — devices property routes to DeviceManager
# ================================================================== #


class TestClientDevicesPairing:
    async def test_list_paired_via_client(self) -> None:
        mock, client = _make_client()
        mock.register("device.pair.list", _PAIR_LIST_RESPONSE)

        result = await client.devices.list_paired()

        mock.assert_called("device.pair.list")
        assert "paired" in result

    async def test_approve_pairing_via_client(self) -> None:
        mock, client = _make_client()
        mock.register("device.pair.approve", {"ok": True})

        result = await client.devices.approve_pairing("req_001")

        mock.assert_called("device.pair.approve")
        assert result["ok"] is True

    async def test_reject_pairing_via_client(self) -> None:
        mock, client = _make_client()
        mock.register("device.pair.reject", {"ok": True})

        result = await client.devices.reject_pairing("req_002")

        mock.assert_called("device.pair.reject")
        assert result["ok"] is True

    async def test_remove_device_via_client(self) -> None:
        mock, client = _make_client()
        mock.register("device.pair.remove", {"ok": True})

        result = await client.devices.remove_device("dev_001")

        mock.assert_called("device.pair.remove")
        assert result["ok"] is True
