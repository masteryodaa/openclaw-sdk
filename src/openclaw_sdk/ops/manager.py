"""OpsManager — wrapper around gateway operational methods.

Verified methods:
- ``logs.tail`` — takes ``{}`` (no params), returns ``{file, cursor, size, lines}``
- ``usage.status`` — takes ``{}``, returns ``{updatedAt, providers: [...]}``
- ``usage.cost`` — takes ``{}``, returns ``{updatedAt, days, daily: [...], totals: {...}}``
- ``sessions.usage`` — takes ``{}``, returns ``{updatedAt, startDate, endDate, sessions: [...]}``
- ``system-event`` — takes ``{text}``, returns ok
- ``last-heartbeat`` — takes ``{}``, returns ``{ts, status, reason, durationMs}``
- ``set-heartbeats`` — takes ``{enabled: bool}``, returns ok
- ``update.run`` — takes ``{}``, returns ``{ok, result, restart, sentinel}``
- ``secrets.reload`` — takes ``{}``, returns ``{ok, warningCount}``

Backward-compat:
- ``usage_summary()`` — aggregation workaround from ``sessions.list`` (kept as alias)
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

    async def usage_status(self) -> dict[str, Any]:
        """Get provider usage status (quotas, limits, plans).

        Gateway method: ``usage.status``

        Returns:
            ``{updatedAt, providers: [{provider, displayName, windows, plan}]}``
        """
        return await self._gateway.call("usage.status", {})

    async def usage_cost(self) -> dict[str, Any]:
        """Get detailed cost breakdown (daily + totals).

        Gateway method: ``usage.cost``

        Returns:
            ``{updatedAt, days, daily: [{date, input, output, ...}], totals: {...}}``
        """
        return await self._gateway.call("usage.cost", {})

    async def sessions_usage(self) -> dict[str, Any]:
        """Get per-session usage analytics.

        Gateway method: ``sessions.usage``

        Returns:
            ``{updatedAt, startDate, endDate, sessions: [{key, sessionId, agentId, usage: {...}}]}``
        """
        return await self._gateway.call("sessions.usage", {})

    async def system_status(self) -> dict[str, Any]:
        """Get gateway system status.

        Gateway method: ``status``

        Returns:
            Dict with ``linkChannel``, ``heartbeat``, ``channelSummary``,
            ``queuedSystemEvents``, and ``sessions`` summary.
        """
        return await self._gateway.call("status", {})

    async def memory_status(self) -> dict[str, Any]:
        """Get memory/embedding health status.

        Gateway method: ``doctor.memory.status``

        Returns:
            Dict with ``agentId``, ``provider``, and ``embedding``
            (containing ``ok`` and optional ``error``).
        """
        return await self._gateway.call("doctor.memory.status", {})

    async def system_event(self, text: str) -> dict[str, Any]:
        """Emit a system event.

        Gateway method: ``system-event``
        Verified params: ``{text}``

        Args:
            text: The system event text to emit.
        """
        return await self._gateway.call("system-event", {"text": text})

    async def last_heartbeat(self) -> dict[str, Any]:
        """Get last heartbeat info.

        Gateway method: ``last-heartbeat``

        Returns:
            ``{ts, status, reason, durationMs}``
        """
        return await self._gateway.call("last-heartbeat", {})

    async def set_heartbeats(self, enabled: bool) -> dict[str, Any]:
        """Enable or disable heartbeats.

        Gateway method: ``set-heartbeats``
        Verified params: ``{enabled: bool}``

        Args:
            enabled: Whether heartbeats should be enabled.
        """
        return await self._gateway.call("set-heartbeats", {"enabled": enabled})

    async def update_run(self) -> dict[str, Any]:
        """Run a system update.

        Gateway method: ``update.run``

        Returns:
            ``{ok, result: {status, mode, ...}, restart, sentinel}``
        """
        return await self._gateway.call("update.run", {})

    async def secrets_reload(self) -> dict[str, Any]:
        """Reload secrets from disk.

        Gateway method: ``secrets.reload``

        Returns:
            ``{ok, warningCount}``
        """
        return await self._gateway.call("secrets.reload", {})

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
