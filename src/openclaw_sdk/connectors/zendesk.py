"""Zendesk connector — tickets, users, and support operations."""

from __future__ import annotations

import base64
from typing import Any

import structlog

from openclaw_sdk.connectors.base import Connector, ConnectorAction, ConnectorConfig

logger = structlog.get_logger(__name__)


class ZendeskConnector(Connector):
    """Connector for the Zendesk Support API v2.

    ``base_url`` must include the Zendesk subdomain
    (e.g. ``"https://yourorg.zendesk.com/api/v2"``).

    Authentication uses email + API token:
    - ``api_key`` = ``"agent@company.com"``
    - ``api_secret`` = Zendesk API token

    The Basic auth credentials are ``email/token:api_token`` as required by
    the Zendesk API.

    Usage::

        config = ConnectorConfig(
            api_key="agent@co.com",
            api_secret="zd_token_xxx",
            base_url="https://myco.zendesk.com/api/v2",
        )
        async with ZendeskConnector(config) as zd:
            tickets = await zd.list_tickets(status="open")
    """

    DEFAULT_BASE_URL = ""  # must be configured per instance

    def __init__(self, config: ConnectorConfig) -> None:
        super().__init__(config)

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            **self._config.extra_headers,
        }
        if self._config.api_key and self._config.api_secret:
            # Zendesk token auth: {email}/token:{api_token}
            creds = f"{self._config.api_key}/token:{self._config.api_secret}"
            b64 = base64.b64encode(creds.encode()).decode("ascii")
            headers["Authorization"] = f"Basic {b64}"
        return headers

    def list_actions(self) -> list[ConnectorAction]:
        return [
            ConnectorAction(
                name="list_tickets",
                description="List support tickets",
                optional_params=["status", "per_page"],
            ),
            ConnectorAction(
                name="get_ticket",
                description="Get a single ticket by ID",
                required_params=["ticket_id"],
            ),
            ConnectorAction(
                name="create_ticket",
                description="Create a new support ticket",
                required_params=["subject", "description"],
                optional_params=["priority"],
            ),
            ConnectorAction(
                name="update_ticket",
                description="Update an existing ticket",
                required_params=["ticket_id", "fields"],
            ),
        ]

    async def list_tickets(
        self, status: str | None = None, per_page: int = 25
    ) -> dict[str, Any]:
        """List support tickets.

        Args:
            status: Filter by status (``"new"``, ``"open"``, ``"pending"``,
                ``"solved"``, ``"closed"``). ``None`` returns all.
            per_page: Number of tickets per page.

        Returns:
            Zendesk response with ``tickets`` array.
        """
        client = self._ensure_connected()
        params: dict[str, Any] = {"per_page": per_page}
        if status:
            params["status"] = status
        resp = await client.get("/tickets.json", params=params)
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result

    async def get_ticket(self, ticket_id: int) -> dict[str, Any]:
        """Get a single ticket by ID.

        Args:
            ticket_id: The Zendesk ticket ID.

        Returns:
            Response with ``ticket`` object.
        """
        client = self._ensure_connected()
        resp = await client.get(f"/tickets/{ticket_id}.json")
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result

    async def create_ticket(
        self,
        subject: str,
        description: str,
        priority: str = "normal",
    ) -> dict[str, Any]:
        """Create a new support ticket.

        Args:
            subject: Ticket subject line.
            description: Ticket body / first comment.
            priority: Ticket priority (``"low"``, ``"normal"``, ``"high"``,
                ``"urgent"``).

        Returns:
            Response with created ``ticket`` object.
        """
        client = self._ensure_connected()
        resp = await client.post(
            "/tickets.json",
            json={
                "ticket": {
                    "subject": subject,
                    "comment": {"body": description},
                    "priority": priority,
                }
            },
        )
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result

    async def update_ticket(
        self, ticket_id: int, fields: dict[str, Any]
    ) -> dict[str, Any]:
        """Update an existing ticket.

        Args:
            ticket_id: The Zendesk ticket ID.
            fields: Dictionary of ticket fields to update (e.g.
                ``{"status": "solved", "priority": "high"}``).

        Returns:
            Response with updated ``ticket`` object.
        """
        client = self._ensure_connected()
        resp = await client.put(
            f"/tickets/{ticket_id}.json",
            json={"ticket": fields},
        )
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result
