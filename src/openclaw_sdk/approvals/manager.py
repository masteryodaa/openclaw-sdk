"""ApprovalManager -- wrapper for execution-approval workflows.

Pending approvals are delivered as **push events** (``approval.requested``)
via ``Gateway.subscribe()``.  There is no RPC method to list pending
approvals (verified 2026-02-21 against OpenClaw 2026.2.3-1).

However, ``exec.approval.resolve`` **does** exist as an RPC method and is
used to approve or deny a pending execution request.

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
