from __future__ import annotations

from typing import Any

from openclaw_sdk.gateway.base import GatewayProtocol


class ChannelManager:
    """Thin wrapper around gateway channel methods.

    Verified method names (from protocol-notes.md):
    - channels.status  (NOT channels.list — that is INVALID)
    - channels.logout
    - web.login.start
    - web.login.wait
    """

    def __init__(self, gateway: GatewayProtocol) -> None:
        self._gateway = gateway

    async def status(self) -> dict[str, Any]:
        """Return full channel status for all configured channels.

        Gateway method: channels.status
        Returns shape: {channelOrder, channelLabels, channels: {<name>: {configured, linked, ...}}}
        """
        return await self._gateway.call("channels.status", {})

    async def logout(self, channel: str) -> bool:
        """Log out of the given channel.

        Gateway method: channels.logout
        """
        await self._gateway.call("channels.logout", {"channel": channel})
        return True

    async def web_login_start(self, channel: str) -> dict[str, Any]:
        """Start a web-based QR login flow for the given channel.

        Gateway method: web.login.start
        Returns: {"qrDataUrl": "data:image/png;base64,..."}
        """
        return await self._gateway.call("web.login.start", {"channel": channel})

    async def web_login_wait(
        self, channel: str, timeout_ms: int = 120000
    ) -> dict[str, Any]:
        """Wait for QR scan completion during a web login flow.

        Gateway method: web.login.wait
        Blocks until the QR code is scanned or the timeout expires.
        """
        return await self._gateway.call(
            "web.login.wait",
            {"channel": channel, "timeoutMs": timeout_ms},
        )
