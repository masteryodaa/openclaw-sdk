"""HubSpot connector — contacts, deals, and CRM objects."""

from __future__ import annotations

from typing import Any

import structlog

from openclaw_sdk.connectors.base import Connector, ConnectorAction, ConnectorConfig

logger = structlog.get_logger(__name__)


class HubSpotConnector(Connector):
    """Connector for the HubSpot CRM API v3.

    Uses a private app access token passed as ``api_key``.

    Usage::

        config = ConnectorConfig(api_key="pat-xxx")
        async with HubSpotConnector(config) as hs:
            contacts = await hs.list_contacts(limit=10)
    """

    DEFAULT_BASE_URL = "https://api.hubapi.com"

    def __init__(self, config: ConnectorConfig) -> None:
        super().__init__(config)

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            **self._config.extra_headers,
        }
        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"
        return headers

    def list_actions(self) -> list[ConnectorAction]:
        return [
            ConnectorAction(
                name="list_contacts",
                description="List CRM contacts",
                optional_params=["limit"],
            ),
            ConnectorAction(
                name="create_contact",
                description="Create a new contact",
                required_params=["email"],
                optional_params=["properties"],
            ),
            ConnectorAction(
                name="list_deals",
                description="List CRM deals",
                optional_params=["limit"],
            ),
            ConnectorAction(
                name="get_deal",
                description="Get a single deal by ID",
                required_params=["deal_id"],
            ),
        ]

    async def list_contacts(self, limit: int = 10) -> dict[str, Any]:
        """List CRM contacts.

        Args:
            limit: Maximum number of contacts to return.

        Returns:
            HubSpot response with ``results`` array of contact objects.
        """
        client = self._ensure_connected()
        resp = await client.get(
            "/crm/v3/objects/contacts",
            params={"limit": limit},
        )
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result

    async def create_contact(
        self,
        email: str,
        properties: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Create a new CRM contact.

        Args:
            email: Contact email address (required by HubSpot).
            properties: Additional contact properties (e.g. ``firstname``,
                ``lastname``, ``phone``).

        Returns:
            Created contact object.
        """
        client = self._ensure_connected()
        props: dict[str, str] = {"email": email}
        if properties:
            props.update(properties)
        resp = await client.post(
            "/crm/v3/objects/contacts",
            json={"properties": props},
        )
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result

    async def list_deals(self, limit: int = 10) -> dict[str, Any]:
        """List CRM deals.

        Args:
            limit: Maximum number of deals to return.

        Returns:
            HubSpot response with ``results`` array of deal objects.
        """
        client = self._ensure_connected()
        resp = await client.get(
            "/crm/v3/objects/deals",
            params={"limit": limit},
        )
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result

    async def get_deal(self, deal_id: str) -> dict[str, Any]:
        """Get a single deal by ID.

        Args:
            deal_id: The HubSpot deal ID.

        Returns:
            Deal object with properties and metadata.
        """
        client = self._ensure_connected()
        resp = await client.get(f"/crm/v3/objects/deals/{deal_id}")
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result
