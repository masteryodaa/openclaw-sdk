"""DeviceManager — manage device tokens and pairing."""

from __future__ import annotations

from typing import Any

from openclaw_sdk.gateway.base import GatewayProtocol


class DeviceManager:
    """Manage device tokens for multi-device access.

    OpenClaw supports multiple connected devices (CLI, web UI, mobile nodes).
    Each device has an auth token that can be rotated or revoked.

    Usage::

        async with OpenClawClient.connect() as client:
            result = await client.devices.rotate_token("device_abc", "operator")
            await client.devices.revoke_token("device_abc", "node")
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
