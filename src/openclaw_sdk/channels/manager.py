from __future__ import annotations

from typing import Any

from openclaw_sdk.gateway.base import GatewayProtocol


class ChannelManager:
    """Thin wrapper around gateway channel methods.

    Verified method names (against live OpenClaw 2026.2.3-1):

    - ``channels.status``  → ``{}`` (no params)
    - ``channels.logout``  → ``{channel}``
    - ``web.login.start``  → ``{}`` (no params) — returns QR data URL
    - ``web.login.wait``   → ``{timeoutMs?}`` (no channel param)
    """

    def __init__(self, gateway: GatewayProtocol) -> None:
        self._gateway = gateway

    async def status(self) -> dict[str, Any]:
        """Return full channel status for all configured channels.

        Gateway method: ``channels.status``

        Returns:
            ``{channelOrder, channelLabels, channelMeta, channels: {<name>: {configured, linked, …}}}``
        """
        return await self._gateway.call("channels.status", {})

    async def logout(self, channel: str) -> bool:
        """Log out of the given channel.

        Gateway method: ``channels.logout``
        Verified params: ``{channel}`` (required).
        """
        await self._gateway.call("channels.logout", {"channel": channel})
        return True

    async def web_login_start(self) -> dict[str, Any]:
        """Start a web-based QR login flow.

        Gateway method: ``web.login.start``
        Verified params: ``{}`` (no params — gateway auto-selects the channel).

        Returns:
            ``{"qrDataUrl": "data:image/png;base64,..."}``
        """
        return await self._gateway.call("web.login.start", {})

    async def web_login_wait(self, timeout_ms: int = 120000) -> dict[str, Any]:
        """Wait for QR scan completion during a web login flow.

        Gateway method: ``web.login.wait``
        Verified params: ``{timeoutMs?}`` (no channel param).
        Blocks until the QR code is scanned or the timeout expires.

        Returns:
            ``{connected: bool, message: str}``
        """
        return await self._gateway.call(
            "web.login.wait",
            {"timeoutMs": timeout_ms},
        )

    async def login(self) -> dict[str, Any]:
        """Start a login flow (alias for :meth:`web_login_start`).

        Returns the QR data URL for scanning.  For pairing-code based
        authentication, call :meth:`request_pairing_code` instead.

        Gateway method: ``web.login.start``
        """
        return await self.web_login_start()

    async def request_pairing_code(
        self, phone: str | None = None
    ) -> dict[str, Any]:
        """Request a numeric pairing code (instead of QR).

        Gateway method: ``web.login.start`` (with ``pairing=true``)

        Args:
            phone: Optional phone number in international format for WhatsApp.

        Returns:
            Gateway response dict, typically containing a ``pairingCode`` field.
        """
        params: dict[str, Any] = {"pairing": True}
        if phone is not None:
            params["phone"] = phone
        return await self._gateway.call("web.login.start", params)
