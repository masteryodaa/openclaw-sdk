"""ApprovalManager — wrapper for execution-approval workflows.

``approvals.list`` and ``approvals.resolve`` **do not exist** as gateway
RPC methods (verified 2026-02-21 against OpenClaw 2026.2.3-1).
Approvals in OpenClaw are delivered as **push events**
(``approval.requested``) via ``Gateway.subscribe()``.

Both methods raise ``NotImplementedError`` with a helpful message
so callers know to use the event-based pattern instead.
"""

from __future__ import annotations

from typing import Any, Literal

from openclaw_sdk.gateway.base import GatewayProtocol


class ApprovalManager:
    """Manage pending execution approvals.

    When an agent operates in ``"confirm"`` permission mode it pauses before
    executing dangerous tools (shell commands, file writes, etc.) and emits
    an ``approval.requested`` push event.

    **Listen for approvals via events, not RPC**::

        async for event in await client.gateway.subscribe():
            if event.event_type == "approval.requested":
                # handle approval
                pass
    """

    def __init__(self, gateway: GatewayProtocol) -> None:
        self._gateway = gateway

    async def list_requests(self) -> list[dict[str, Any]]:
        """List all pending approval requests.

        Raises:
            NotImplementedError: ``approvals.list`` does not exist on the
                OpenClaw gateway.  Approvals are push-event based.
        """
        raise NotImplementedError(
            "approvals.list does not exist on the OpenClaw gateway. "
            "Approvals are delivered as push events (approval.requested) "
            "via gateway.subscribe(). See ApprovalManager docstring."
        )

    async def resolve(
        self,
        request_id: str,
        decision: Literal["approve", "deny"],
        note: str | None = None,
    ) -> dict[str, Any]:
        """Approve or deny a pending request.

        Raises:
            NotImplementedError: ``approvals.resolve`` does not exist on the
                OpenClaw gateway.
        """
        raise NotImplementedError(
            "approvals.resolve does not exist on the OpenClaw gateway. "
            "Approval resolution may be handled via push events."
        )
