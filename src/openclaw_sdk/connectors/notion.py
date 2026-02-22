"""Notion connector — search, pages, and databases."""

from __future__ import annotations

from typing import Any

import structlog

from openclaw_sdk.connectors.base import Connector, ConnectorAction, ConnectorConfig

logger = structlog.get_logger(__name__)

# Notion requires a specific API version header on all requests.
_NOTION_VERSION = "2022-06-28"


class NotionConnector(Connector):
    """Connector for the Notion API.

    Uses an internal integration token passed as ``api_key``.

    Usage::

        config = ConnectorConfig(api_key="ntn_xxx")
        async with NotionConnector(config) as notion:
            results = await notion.search("Project Plan")
    """

    DEFAULT_BASE_URL = "https://api.notion.com/v1"

    def __init__(self, config: ConnectorConfig) -> None:
        super().__init__(config)

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Notion-Version": _NOTION_VERSION,
            **self._config.extra_headers,
        }
        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"
        return headers

    def list_actions(self) -> list[ConnectorAction]:
        return [
            ConnectorAction(
                name="search",
                description="Search across all pages and databases",
                optional_params=["query"],
            ),
            ConnectorAction(
                name="get_page",
                description="Retrieve a page by ID",
                required_params=["page_id"],
            ),
            ConnectorAction(
                name="create_page",
                description="Create a new page inside a parent page or database",
                required_params=["parent_id", "properties"],
            ),
            ConnectorAction(
                name="get_database",
                description="Retrieve a database by ID",
                required_params=["database_id"],
            ),
        ]

    async def search(self, query: str = "") -> dict[str, Any]:
        """Search Notion for pages and databases.

        Args:
            query: Search text. Empty string returns recent pages.

        Returns:
            Search results with ``results`` array.
        """
        client = self._ensure_connected()
        payload: dict[str, Any] = {}
        if query:
            payload["query"] = query
        resp = await client.post("/search", json=payload)
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result

    async def get_page(self, page_id: str) -> dict[str, Any]:
        """Retrieve a Notion page by ID.

        Args:
            page_id: The page UUID (with or without dashes).

        Returns:
            Page object with properties and metadata.
        """
        client = self._ensure_connected()
        resp = await client.get(f"/pages/{page_id}")
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result

    async def create_page(
        self,
        parent_id: str,
        properties: dict[str, Any],
        is_database: bool = False,
    ) -> dict[str, Any]:
        """Create a new page in Notion.

        Args:
            parent_id: Parent page or database UUID.
            properties: Page properties (title, etc.).
            is_database: If ``True``, ``parent_id`` is treated as a database ID;
                otherwise as a page ID.

        Returns:
            Created page object.
        """
        client = self._ensure_connected()
        if is_database:
            parent: dict[str, Any] = {"database_id": parent_id}
        else:
            parent = {"page_id": parent_id}
        resp = await client.post(
            "/pages",
            json={"parent": parent, "properties": properties},
        )
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result

    async def get_database(self, database_id: str) -> dict[str, Any]:
        """Retrieve a Notion database by ID.

        Args:
            database_id: The database UUID.

        Returns:
            Database object with schema and metadata.
        """
        client = self._ensure_connected()
        resp = await client.get(f"/databases/{database_id}")
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result
