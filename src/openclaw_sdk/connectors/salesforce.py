"""Salesforce connector — SOQL queries, sObject CRUD."""

from __future__ import annotations

from typing import Any

import structlog

from openclaw_sdk.connectors.base import Connector, ConnectorAction, ConnectorConfig

logger = structlog.get_logger(__name__)

# Salesforce REST API version
_SF_API_VERSION = "v58.0"


class SalesforceConnector(Connector):
    """Connector for the Salesforce REST API.

    ``base_url`` must be set to your Salesforce instance URL
    (e.g. ``"https://yourorg.my.salesforce.com"``).  Pass the OAuth access
    token as ``api_key``.

    Usage::

        config = ConnectorConfig(
            api_key="00Dxx0000...",
            base_url="https://yourorg.my.salesforce.com",
        )
        async with SalesforceConnector(config) as sf:
            result = await sf.query("SELECT Id, Name FROM Account LIMIT 10")
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
        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"
        return headers

    @property
    def _api_prefix(self) -> str:
        """Return the API path prefix including version."""
        return f"/services/data/{_SF_API_VERSION}"

    def list_actions(self) -> list[ConnectorAction]:
        return [
            ConnectorAction(
                name="query",
                description="Execute a SOQL query",
                required_params=["soql"],
            ),
            ConnectorAction(
                name="get_record",
                description="Get a single sObject record",
                required_params=["sobject", "record_id"],
            ),
            ConnectorAction(
                name="create_record",
                description="Create a new sObject record",
                required_params=["sobject", "fields"],
            ),
            ConnectorAction(
                name="update_record",
                description="Update an existing sObject record",
                required_params=["sobject", "record_id", "fields"],
            ),
        ]

    async def query(self, soql: str) -> dict[str, Any]:
        """Execute a SOQL query.

        Args:
            soql: A valid SOQL query string.

        Returns:
            Query result with ``records`` array and ``totalSize``.
        """
        client = self._ensure_connected()
        resp = await client.get(
            f"{self._api_prefix}/query",
            params={"q": soql},
        )
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result

    async def get_record(
        self, sobject: str, record_id: str
    ) -> dict[str, Any]:
        """Get a single sObject record by ID.

        Args:
            sobject: sObject type (e.g. ``"Account"``, ``"Contact"``).
            record_id: The Salesforce record ID.

        Returns:
            Record object with all fields.
        """
        client = self._ensure_connected()
        resp = await client.get(
            f"{self._api_prefix}/sobjects/{sobject}/{record_id}",
        )
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result

    async def create_record(
        self, sobject: str, fields: dict[str, Any]
    ) -> dict[str, Any]:
        """Create a new sObject record.

        Args:
            sobject: sObject type (e.g. ``"Account"``).
            fields: Field name/value pairs for the new record.

        Returns:
            API response with ``id`` and ``success`` flag.
        """
        client = self._ensure_connected()
        resp = await client.post(
            f"{self._api_prefix}/sobjects/{sobject}",
            json=fields,
        )
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result

    async def update_record(
        self, sobject: str, record_id: str, fields: dict[str, Any]
    ) -> None:
        """Update an existing sObject record.

        Salesforce PATCH returns 204 No Content on success.

        Args:
            sobject: sObject type (e.g. ``"Account"``).
            record_id: The Salesforce record ID.
            fields: Field name/value pairs to update.
        """
        client = self._ensure_connected()
        resp = await client.patch(
            f"{self._api_prefix}/sobjects/{sobject}/{record_id}",
            json=fields,
        )
        resp.raise_for_status()
