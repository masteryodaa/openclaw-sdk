"""ApprovalManager -- wrapper for execution-approval workflows.

Provides the full approval lifecycle:

- **resolve** -- approve or deny a pending execution request
- **request** -- request approval for a command (blocks until resolved)
- **wait_decision** -- wait for an approval decision by id
- **get_settings / set_settings** -- read/write the approval config file
- **get_node_settings / set_node_settings** -- proxied node-level settings

Pending approvals are delivered as **push events** (``approval.requested``)
via ``Gateway.subscribe()``.

Typical workflow::

    # 1. Subscribe for approval events
    async for event in await client.gateway.subscribe(["approval.requested"]):
        request_id = event.data["id"]
        # 2. Decide whether to approve or deny
        result = await client.approvals.resolve(request_id, "approve")
"""

from __future__ import annotations

from typing import Any, Literal

from openclaw_sdk.gateway.base import GatewayProtocol


class ApprovalManager:
    """Manage pending execution approvals.

    When an agent operates in ``"confirm"`` permission mode it pauses before
    executing dangerous tools (shell commands, file writes, etc.) and emits
    an ``approval.requested`` push event.

    **Listen for approvals via events, resolve via RPC**::

        async for event in await client.gateway.subscribe(["approval.requested"]):
            request_id = event.data["id"]
            await client.approvals.resolve(request_id, "approve")
    """

    def __init__(self, gateway: GatewayProtocol) -> None:
        self._gateway = gateway

    # ------------------------------------------------------------------ #
    # exec.approval.resolve (existing)
    # ------------------------------------------------------------------ #

    async def resolve(
        self,
        request_id: str,
        decision: Literal["approve", "deny"],
    ) -> dict[str, Any]:
        """Approve or deny a pending execution request.

        Gateway method: ``exec.approval.resolve``
        Verified params: ``{id, decision}``

        Args:
            request_id: The approval request identifier (from the push event).
            decision: ``"approve"`` or ``"deny"``.

        Returns:
            Gateway response dict.
        """
        return await self._gateway.call(
            "exec.approval.resolve",
            {"id": request_id, "decision": decision},
        )

    # ------------------------------------------------------------------ #
    # exec.approval.request
    # ------------------------------------------------------------------ #

    async def request(
        self,
        command: str,
        *,
        timeout_ms: int | None = None,
        agent_id: str | None = None,
        session_key: str | None = None,
        node_id: str | None = None,
    ) -> dict[str, Any]:
        """Request approval for a command execution. Blocks until resolved.

        Gateway method: ``exec.approval.request``

        Args:
            command: The command string to request approval for.
            timeout_ms: Optional timeout in milliseconds.
            agent_id: Optional agent identifier.
            session_key: Optional session key.
            node_id: Optional node identifier.

        Returns:
            ``{id, decision, createdAtMs, expiresAtMs}``.
            Decision: ``"allow-once"`` | ``"allow-always"`` | ``"deny"`` | null (expired).
        """
        params: dict[str, Any] = {"command": command}
        if timeout_ms is not None:
            params["timeoutMs"] = timeout_ms
        if agent_id is not None:
            params["agentId"] = agent_id
        if session_key is not None:
            params["sessionKey"] = session_key
        if node_id is not None:
            params["nodeId"] = node_id
        return await self._gateway.call("exec.approval.request", params)

    # ------------------------------------------------------------------ #
    # exec.approval.waitDecision
    # ------------------------------------------------------------------ #

    async def wait_decision(self, approval_id: str) -> dict[str, Any]:
        """Wait for an approval decision. Blocks until resolved.

        Gateway method: ``exec.approval.waitDecision``

        Args:
            approval_id: The approval request identifier.

        Returns:
            ``{id, decision, createdAtMs, expiresAtMs}``.
        """
        return await self._gateway.call(
            "exec.approval.waitDecision", {"id": approval_id}
        )

    # ------------------------------------------------------------------ #
    # exec.approvals.get / set (settings)
    # ------------------------------------------------------------------ #

    async def get_settings(self) -> dict[str, Any]:
        """Get the approval settings/config.

        Gateway method: ``exec.approvals.get``

        Returns:
            ``{path, exists, hash, file: {version, socket, defaults, agents}}``.
        """
        return await self._gateway.call("exec.approvals.get", {})

    async def set_settings(
        self, file: dict[str, Any], base_hash: str | None = None
    ) -> dict[str, Any]:
        """Set approval settings with optimistic concurrency.

        Gateway method: ``exec.approvals.set``

        Args:
            file: The approval settings object (must include ``version``).
            base_hash: Optional hash for optimistic concurrency control.

        Returns:
            Same structure as :meth:`get_settings`.
        """
        params: dict[str, Any] = {"file": file}
        if base_hash is not None:
            params["baseHash"] = base_hash
        return await self._gateway.call("exec.approvals.set", params)

    # ------------------------------------------------------------------ #
    # exec.approvals.node.get / set (node-proxied settings)
    # ------------------------------------------------------------------ #

    async def get_node_settings(self, node_id: str) -> dict[str, Any]:
        """Get node-level approval settings. Proxied to node.

        Gateway method: ``exec.approvals.node.get``
        Unavailable if the node is not connected.

        Args:
            node_id: The target node identifier.

        Returns:
            Node-specific approval settings.
        """
        return await self._gateway.call("exec.approvals.node.get", {"nodeId": node_id})

    async def set_node_settings(
        self,
        node_id: str,
        file: dict[str, Any],
        base_hash: str | None = None,
    ) -> dict[str, Any]:
        """Set node-level approval settings. Proxied to node.

        Gateway method: ``exec.approvals.node.set``

        Args:
            node_id: The target node identifier.
            file: The approval settings object (must include ``version``).
            base_hash: Optional hash for optimistic concurrency control.

        Returns:
            Updated node-specific approval settings.
        """
        params: dict[str, Any] = {"nodeId": node_id, "file": file}
        if base_hash is not None:
            params["baseHash"] = base_hash
        return await self._gateway.call("exec.approvals.node.set", params)
