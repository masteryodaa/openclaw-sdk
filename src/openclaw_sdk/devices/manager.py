"""DeviceManager — manage device tokens, pairing, and multi-device access."""

from __future__ import annotations

from typing import Any

from openclaw_sdk.gateway.base import GatewayProtocol


class DeviceManager:
    """Manage device tokens and pairing for multi-device access.

    OpenClaw supports multiple connected devices (CLI, web UI, mobile nodes).
    Each device has an auth token that can be rotated or revoked.  Devices
    can also be paired, approved, rejected, and removed.

    Usage::

        async with OpenClawClient.connect() as client:
            # Token management
            result = await client.devices.rotate_token("device_abc", "operator")
            await client.devices.revoke_token("device_abc", "node")

            # Pairing workflow
            devices = await client.devices.list_paired()
            await client.devices.approve_pairing("req_123")
            await client.devices.reject_pairing("req_456")
            await client.devices.remove_device("device_abc")
    """

    def __init__(self, gateway: GatewayProtocol) -> None:
        self._gateway = gateway

    async def rotate_token(self, device_id: str, role: str) -> dict[str, Any]:
        """Rotate the auth token for a device.

        Gateway method: ``device.token.rotate``
        Verified params: ``{deviceId, role}``

        Args:
            device_id: The device identifier.
            role: The device's role (e.g. ``"operator"``, ``"node"``).

        Returns:
            Gateway response dict (typically contains the new token).
        """
        return await self._gateway.call(
            "device.token.rotate", {"deviceId": device_id, "role": role}
        )

    async def revoke_token(self, device_id: str, role: str) -> dict[str, Any]:
        """Revoke the auth token for a device.

        Gateway method: ``device.token.revoke``
        Verified params: ``{deviceId, role}``

        Args:
            device_id: The device identifier.
            role: The device's role (e.g. ``"operator"``, ``"node"``).

        Returns:
            Gateway response dict.
        """
        return await self._gateway.call(
            "device.token.revoke", {"deviceId": device_id, "role": role}
        )

    # ------------------------------------------------------------------ #
    # Pairing workflow
    # ------------------------------------------------------------------ #

    async def list_paired(self) -> dict[str, Any]:
        """List all pending and paired devices.

        Gateway method: ``device.pair.list``

        Returns:
            Dict with ``pending`` and ``paired`` arrays.
        """
        return await self._gateway.call("device.pair.list", {})

    async def approve_pairing(self, request_id: str) -> dict[str, Any]:
        """Approve a device pairing request.

        Gateway method: ``device.pair.approve``

        Args:
            request_id: The pairing request identifier.

        Returns:
            Gateway response dict.
        """
        return await self._gateway.call(
            "device.pair.approve", {"requestId": request_id}
        )

    async def reject_pairing(self, request_id: str) -> dict[str, Any]:
        """Reject a device pairing request.

        Gateway method: ``device.pair.reject``

        Args:
            request_id: The pairing request identifier.

        Returns:
            Gateway response dict.
        """
        return await self._gateway.call("device.pair.reject", {"requestId": request_id})

    async def remove_device(self, device_id: str) -> dict[str, Any]:
        """Remove a paired device.

        Gateway method: ``device.pair.remove``

        Args:
            device_id: The device identifier to remove.

        Returns:
            Gateway response dict.
        """
        return await self._gateway.call("device.pair.remove", {"deviceId": device_id})
