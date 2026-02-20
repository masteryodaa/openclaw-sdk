"""OpsManager — wrapper around gateway operational methods.

Verified methods:
- ``logs.tail`` — takes ``{}`` (no params), returns ``{file, cursor, size, lines}``

Unverified / removed:
- ``update.run`` — not confirmed to exist on the gateway
- ``usage.summary`` — does NOT exist; usage data is in session metadata
"""

from __future__ import annotations

from typing import Any

from openclaw_sdk.gateway.base import GatewayProtocol


class OpsManager:
    """Operational utilities: log tailing and usage reporting.

    Usage::

        async with OpenClawClient.connect() as client:
            logs = await client.ops.logs_tail()
            usage = await client.ops.usage_summary()
    """

    def __init__(self, gateway: GatewayProtocol) -> None:
        self._gateway = gateway

    async def logs_tail(self) -> dict[str, Any]:
        """Fetch the most recent log entries.

        Gateway method: ``logs.tail``
        Verified params: ``{}`` — no parameters accepted.

        Returns:
            ``{file, cursor, size, lines: [...]}``
        """
        return await self._gateway.call("logs.tail", {})

    async def usage_summary(self) -> dict[str, Any]:
        """Return aggregated token-usage statistics from session metadata.

        ``usage.summary`` does **not** exist as a gateway RPC method
        (verified 2026-02-21).  Usage data is embedded in each session
        object (``inputTokens``, ``outputTokens``, ``totalTokens``).
        This method aggregates it from ``sessions.list``.

        Returns:
            Dict with ``totalInputTokens``, ``totalOutputTokens``,
            ``totalTokens``, and ``sessionCount``.
        """
        result = await self._gateway.call("sessions.list", {})
        sessions: list[dict[str, Any]] = result.get("sessions", [])
        total_input = sum(s.get("inputTokens", 0) for s in sessions)
        total_output = sum(s.get("outputTokens", 0) for s in sessions)
        total_tokens = sum(s.get("totalTokens", 0) for s in sessions)
        return {
            "totalInputTokens": total_input,
            "totalOutputTokens": total_output,
            "totalTokens": total_tokens,
            "sessionCount": len(sessions),
        }
