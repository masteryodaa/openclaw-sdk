"""TTSManager -- text-to-speech via gateway RPC.

Verified methods:
- ``tts.enable`` -- takes ``{}``, returns ``{enabled: true}``
- ``tts.disable`` -- takes ``{}``, returns ``{enabled: false}``
- ``tts.convert`` -- takes ``{text}``, returns audio data
- ``tts.setProvider`` -- takes ``{provider}``, returns ok
- ``tts.status`` -- takes ``{}``, returns status dict
- ``tts.providers`` -- takes ``{}``, returns providers list
"""

from __future__ import annotations

from typing import Any

from openclaw_sdk.gateway.base import GatewayProtocol


class TTSManager:
    """Text-to-speech operations via gateway RPC.

    Usage::

        async with OpenClawClient.connect() as client:
            await client.tts.enable()
            voices = await client.tts.providers()
            await client.tts.convert("Hello world")
    """

    def __init__(self, gateway: GatewayProtocol) -> None:
        self._gateway = gateway

    async def enable(self) -> dict[str, Any]:
        """Enable TTS.

        Gateway method: ``tts.enable``

        Returns:
            ``{enabled: true}``
        """
        return await self._gateway.call("tts.enable", {})

    async def disable(self) -> dict[str, Any]:
        """Disable TTS.

        Gateway method: ``tts.disable``

        Returns:
            ``{enabled: false}``
        """
        return await self._gateway.call("tts.disable", {})

    async def convert(self, text: str) -> dict[str, Any]:
        """Convert text to speech audio.

        Gateway method: ``tts.convert``

        Args:
            text: The text to convert to speech.

        Returns:
            Audio data dict from the gateway.
        """
        return await self._gateway.call("tts.convert", {"text": text})

    async def set_provider(self, provider: str) -> dict[str, Any]:
        """Set TTS provider.

        Gateway method: ``tts.setProvider``

        Args:
            provider: Provider name (``"openai"``, ``"elevenlabs"``, or ``"edge"``).

        Returns:
            ``{ok: true}``
        """
        return await self._gateway.call("tts.setProvider", {"provider": provider})

    async def status(self) -> dict[str, Any]:
        """Get TTS status.

        Gateway method: ``tts.status``

        Returns:
            Status dict with current TTS configuration.
        """
        return await self._gateway.call("tts.status", {})

    async def providers(self) -> dict[str, Any]:
        """List available TTS providers.

        Gateway method: ``tts.providers``

        Returns:
            Dict with ``providers`` array.
        """
        return await self._gateway.call("tts.providers", {})
