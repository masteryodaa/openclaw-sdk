"""NodeManager — wrapper around the gateway node / presence namespace."""

from __future__ import annotations

from typing import Any

from openclaw_sdk.gateway.base import GatewayProtocol


class NodeManager:
    """Inspect and invoke OpenClaw nodes.

    In a multi-node OpenClaw setup each process registers itself with the
    gateway.  ``NodeManager`` surfaces the system-presence check and the
    per-node list / describe / invoke primitives.

    Usage::

        async with OpenClawClient.connect() as client:
            presence = await client.nodes.system_presence()
            nodes = await client.nodes.list()
    """

    def __init__(self, gateway: GatewayProtocol) -> None:
        self._gateway = gateway

    async def system_presence(self) -> dict[str, Any]:
        """Return the gateway's system-presence status.

        Gateway method: ``system-presence``

        Returns:
            Dict with presence information (online nodes, uptime, etc.).
        """
        return await self._gateway.call("system-presence", {})

    async def list(self) -> list[dict[str, Any]]:
        """List all registered nodes.

        Gateway method: ``node.list``

        Returns:
            List of node descriptor dicts.
        """
        result = await self._gateway.call("node.list", {})
        nodes: list[dict[str, Any]] = result.get("nodes", [])
        return nodes

    async def describe(self, node_id: str) -> dict[str, Any]:
        """Fetch detailed information about a specific node.

        Gateway method: ``node.describe``

        Args:
            node_id: The node identifier.

        Returns:
            Node descriptor dict.
        """
        return await self._gateway.call("node.describe", {"id": node_id})

    async def invoke(
        self,
        node_id: str,
        action: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Invoke an action on a specific node.

        Gateway method: ``node.invoke``

        Args:
            node_id: The node identifier.
            action: The action name to invoke.
            payload: Optional parameters for the action.

        Returns:
            Gateway response dict.
        """
        params: dict[str, Any] = {"id": node_id, "action": action}
        if payload is not None:
            params["payload"] = payload
        return await self._gateway.call("node.invoke", params)
