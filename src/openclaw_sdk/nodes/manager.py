"""NodeManager — wrapper around the gateway node / presence namespace."""

from __future__ import annotations

from typing import Any

from openclaw_sdk.gateway.base import GatewayProtocol


class NodeManager:
    """Inspect, invoke, rename, and pair OpenClaw nodes.

    In a multi-node OpenClaw setup each process registers itself with the
    gateway.  ``NodeManager`` surfaces the system-presence check, per-node
    list / describe / invoke primitives, node renaming, and pairing
    management (request, approve, reject, verify).

    Two methods are role-restricted and require the ``node`` role:
    :meth:`invoke_result` and :meth:`emit_event`.

    Usage::

        async with OpenClawClient.connect() as client:
            presence = await client.nodes.system_presence()
            nodes = await client.nodes.list()
            await client.nodes.rename("n1", "My Node")
            pairs = await client.nodes.pair_list()
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

    # ------------------------------------------------------------------ #
    # Node rename
    # ------------------------------------------------------------------ #

    async def rename(self, node_id: str, display_name: str) -> dict[str, Any]:
        """Rename a node.

        Gateway method: ``node.rename``

        Args:
            node_id: The node identifier.
            display_name: The new display name.

        Returns:
            Gateway response dict.
        """
        return await self._gateway.call(
            "node.rename", {"nodeId": node_id, "displayName": display_name}
        )

    # ------------------------------------------------------------------ #
    # Role-restricted methods (require ``node`` role)
    # ------------------------------------------------------------------ #

    async def invoke_result(self, **params: Any) -> dict[str, Any]:
        """Submit an invoke result back to the gateway.

        Gateway method: ``node.invoke.result``

        Note:
            Role-restricted — requires ``node`` role.
        """
        return await self._gateway.call("node.invoke.result", params)

    async def emit_event(self, **params: Any) -> dict[str, Any]:
        """Emit a node event.

        Gateway method: ``node.event``

        Note:
            Role-restricted — requires ``node`` role.
        """
        return await self._gateway.call("node.event", params)

    # ------------------------------------------------------------------ #
    # Pairing management
    # ------------------------------------------------------------------ #

    async def pair_request(self, node_id: str) -> dict[str, Any]:
        """Request node pairing.

        Gateway method: ``node.pair.request``

        Args:
            node_id: The node identifier to pair.

        Returns:
            Gateway response dict.
        """
        return await self._gateway.call("node.pair.request", {"nodeId": node_id})

    async def pair_list(self) -> dict[str, Any]:
        """List pending and paired nodes.

        Gateway method: ``node.pair.list``

        Returns:
            Dict with ``pending`` and ``paired`` arrays.
        """
        return await self._gateway.call("node.pair.list", {})

    async def pair_approve(self, request_id: str) -> dict[str, Any]:
        """Approve a node pairing request.

        Gateway method: ``node.pair.approve``

        Args:
            request_id: The pairing request identifier.

        Returns:
            Gateway response dict.
        """
        return await self._gateway.call("node.pair.approve", {"requestId": request_id})

    async def pair_reject(self, request_id: str) -> dict[str, Any]:
        """Reject a node pairing request.

        Gateway method: ``node.pair.reject``

        Args:
            request_id: The pairing request identifier.

        Returns:
            Gateway response dict.
        """
        return await self._gateway.call("node.pair.reject", {"requestId": request_id})

    async def pair_verify(self, node_id: str, token: str) -> dict[str, Any]:
        """Verify a node pairing.

        Gateway method: ``node.pair.verify``

        Args:
            node_id: The node identifier.
            token: The verification token.

        Returns:
            Gateway response dict.
        """
        return await self._gateway.call(
            "node.pair.verify", {"nodeId": node_id, "token": token}
        )
