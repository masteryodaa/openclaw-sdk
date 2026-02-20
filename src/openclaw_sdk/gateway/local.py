from __future__ import annotations

from typing import Any, AsyncIterator

from openclaw_sdk.core.types import HealthStatus, StreamEvent
from openclaw_sdk.gateway.base import Gateway

# LocalGateway will auto-detect and connect to a running local OpenClaw instance.
# Implemented in MD3A after protocol research is validated.
# For now this is a thin stub so imports resolve cleanly.

DEFAULT_WS_URL = "ws://127.0.0.1:18789/gateway"


class LocalGateway(Gateway):
    """Auto-connecting gateway for a locally running OpenClaw instance.

    Full implementation in MD3A (deferred until ProtocolGateway is complete).
    This gateway wraps ProtocolGateway after detecting that OpenClaw is running.
    """

    def __init__(self, ws_url: str = DEFAULT_WS_URL) -> None:
        self._ws_url = ws_url
        self._inner: Gateway | None = None

    async def connect(self) -> None:
        # Implemented in MD3A — imports ProtocolGateway here to avoid circular deps
        from openclaw_sdk.gateway.protocol import ProtocolGateway  # noqa: PLC0415

        self._inner = ProtocolGateway(self._ws_url)
        await self._inner.connect()

    async def close(self) -> None:
        if self._inner is not None:
            await self._inner.close()

    async def health(self) -> HealthStatus:
        if self._inner is None:
            return HealthStatus(healthy=False)
        return await self._inner.health()

    async def call(
        self, method: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        if self._inner is None:
            raise RuntimeError("LocalGateway not connected.")
        return await self._inner.call(method, params)

    async def subscribe(
        self, event_types: list[str] | None = None
    ) -> AsyncIterator[StreamEvent]:
        if self._inner is None:
            raise RuntimeError("LocalGateway not connected.")
        return await self._inner.subscribe(event_types)
