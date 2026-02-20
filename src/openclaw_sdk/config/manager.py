"""ConfigManager — thin wrapper around the gateway ``config.*`` namespace.

All ``config.set``, ``config.patch``, and ``config.apply`` methods use
the **raw config string** format: ``{raw: "<full JSON>", baseHash?: "<hash>"}``.
Call :meth:`ConfigManager.get` first to obtain the current config and its hash
for optimistic concurrency control (compare-and-swap).
"""

from __future__ import annotations

from typing import Any

from openclaw_sdk.gateway.base import GatewayProtocol


class ConfigManager:
    """Manage the OpenClaw runtime configuration via the gateway.

    All methods delegate to ``config.*`` gateway RPC calls.

    Usage::

        async with OpenClawClient.connect() as client:
            cfg = await client.config_mgr.get()
            raw = cfg["raw"]            # current config as JSON string
            base_hash = cfg.get("hash") # for CAS
            # … modify raw …
            await client.config_mgr.set(new_raw)
    """

    def __init__(self, gateway: GatewayProtocol) -> None:
        self._gateway = gateway

    async def get(self) -> dict[str, Any]:
        """Fetch the full current runtime configuration.

        Gateway method: ``config.get``

        Returns:
            ``{path, exists, raw, parsed}`` — ``raw`` is the config file
            contents as a JSON string, ``parsed`` is the deserialized dict.
        """
        return await self._gateway.call("config.get", {})

    async def schema(self) -> dict[str, Any]:
        """Fetch the JSON Schema for the runtime configuration.

        Gateway method: ``config.schema``

        Returns:
            ``{schema: {$schema, type, properties, …}}``
        """
        return await self._gateway.call("config.schema", {})

    async def set(self, raw: str) -> dict[str, Any]:
        """Replace the entire runtime configuration.

        Gateway method: ``config.set``
        Verified params: ``{raw}`` — full config file as a JSON string.

        Args:
            raw: The complete configuration as a JSON string.

        Returns:
            Gateway response dict.
        """
        return await self._gateway.call("config.set", {"raw": raw})

    async def patch(
        self,
        raw: str,
        base_hash: str | None = None,
    ) -> dict[str, Any]:
        """Write a new config with optional optimistic concurrency control.

        Gateway method: ``config.patch``
        Verified params: ``{raw, baseHash?}`` — compare-and-swap on the
        config file.  Call :meth:`get` first to obtain the current hash.

        Args:
            raw: The full configuration as a JSON string.
            base_hash: Optional ETag / base hash for compare-and-swap.

        Returns:
            Gateway response dict.
        """
        params: dict[str, Any] = {"raw": raw}
        if base_hash is not None:
            params["baseHash"] = base_hash
        return await self._gateway.call("config.patch", params)

    async def apply(
        self,
        raw: str,
        base_hash: str | None = None,
    ) -> dict[str, Any]:
        """Apply a new config with optional optimistic concurrency control.

        Gateway method: ``config.apply``
        Params: ``{raw, baseHash?}``

        Args:
            raw: The full configuration as a JSON string.
            base_hash: Optional ETag / base hash for compare-and-swap.

        Returns:
            Gateway response dict.
        """
        params: dict[str, Any] = {"raw": raw}
        if base_hash is not None:
            params["baseHash"] = base_hash
        return await self._gateway.call("config.apply", params)
