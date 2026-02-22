"""Google Sheets connector — read, write, and list spreadsheet data."""

from __future__ import annotations

from typing import Any

import structlog

from openclaw_sdk.connectors.base import Connector, ConnectorAction, ConnectorConfig

logger = structlog.get_logger(__name__)


class GoogleSheetsConnector(Connector):
    """Connector for the Google Sheets API v4.

    Expects an OAuth2 access token or API key passed as ``api_key``.

    Usage::

        config = ConnectorConfig(api_key="ya29.xxx")
        async with GoogleSheetsConnector(config) as sheets:
            data = await sheets.get_values("spreadsheet_id", "Sheet1!A1:C10")
    """

    DEFAULT_BASE_URL = "https://sheets.googleapis.com/v4"

    def __init__(self, config: ConnectorConfig) -> None:
        super().__init__(config)

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {
            "Accept": "application/json",
            **self._config.extra_headers,
        }
        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"
        return headers

    def list_actions(self) -> list[ConnectorAction]:
        return [
            ConnectorAction(
                name="get_values",
                description="Read cell values from a spreadsheet range",
                required_params=["spreadsheet_id", "range"],
            ),
            ConnectorAction(
                name="update_values",
                description="Write values to a spreadsheet range",
                required_params=["spreadsheet_id", "range", "values"],
            ),
            ConnectorAction(
                name="list_sheets",
                description="List all sheets (tabs) in a spreadsheet",
                required_params=["spreadsheet_id"],
            ),
        ]

    async def get_values(
        self, spreadsheet_id: str, range_: str
    ) -> dict[str, Any]:
        """Read values from a spreadsheet range.

        Args:
            spreadsheet_id: The ID of the Google Sheets spreadsheet.
            range_: A1 notation range (e.g. ``"Sheet1!A1:C10"``).

        Returns:
            API response containing ``values`` 2D array.
        """
        client = self._ensure_connected()
        resp = await client.get(
            f"/spreadsheets/{spreadsheet_id}/values/{range_}",
        )
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result

    async def update_values(
        self,
        spreadsheet_id: str,
        range_: str,
        values: list[list[Any]],
    ) -> dict[str, Any]:
        """Write values to a spreadsheet range.

        Args:
            spreadsheet_id: The ID of the Google Sheets spreadsheet.
            range_: A1 notation range to update.
            values: 2D array of values to write.

        Returns:
            API response with update metadata.
        """
        client = self._ensure_connected()
        resp = await client.put(
            f"/spreadsheets/{spreadsheet_id}/values/{range_}",
            params={"valueInputOption": "USER_ENTERED"},
            json={"range": range_, "values": values},
        )
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result

    async def list_sheets(
        self, spreadsheet_id: str
    ) -> dict[str, Any]:
        """List all sheets (tabs) in a spreadsheet.

        Args:
            spreadsheet_id: The ID of the Google Sheets spreadsheet.

        Returns:
            API response with ``sheets`` array containing sheet metadata.
        """
        client = self._ensure_connected()
        resp = await client.get(
            f"/spreadsheets/{spreadsheet_id}",
            params={"fields": "sheets.properties"},
        )
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result
