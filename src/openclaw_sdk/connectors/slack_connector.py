"""Slack connector — messages, channels, users, and file uploads."""

from __future__ import annotations

from typing import Any

import structlog

from openclaw_sdk.connectors.base import Connector, ConnectorAction, ConnectorConfig

logger = structlog.get_logger(__name__)


class SlackConnector(Connector):
    """Connector for the Slack Web API.

    Uses the Bot Token (``xoxb-...``) to send messages, list channels/users,
    and upload files.

    Usage::

        config = ConnectorConfig(api_key="xoxb-xxx")
        async with SlackConnector(config) as slack:
            await slack.send_message("#general", "Hello from OpenClaw!")
    """

    DEFAULT_BASE_URL = "https://slack.com/api"

    def __init__(self, config: ConnectorConfig) -> None:
        super().__init__(config)

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {
            "Content-Type": "application/json; charset=utf-8",
            **self._config.extra_headers,
        }
        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"
        return headers

    def list_actions(self) -> list[ConnectorAction]:
        return [
            ConnectorAction(
                name="send_message",
                description="Send a message to a Slack channel",
                required_params=["channel", "text"],
            ),
            ConnectorAction(
                name="list_channels",
                description="List all public channels in the workspace",
                optional_params=["limit"],
            ),
            ConnectorAction(
                name="post_file",
                description="Upload a text file to a channel",
                required_params=["channel", "content", "filename"],
            ),
            ConnectorAction(
                name="list_users",
                description="List all users in the workspace",
                optional_params=["limit"],
            ),
        ]

    async def send_message(
        self, channel: str, text: str
    ) -> dict[str, Any]:
        """Send a message to a Slack channel.

        Args:
            channel: Channel name (``"#general"``) or ID (``"C01234"``).
            text: Message text.

        Returns:
            Slack API response containing the posted message.
        """
        client = self._ensure_connected()
        resp = await client.post(
            "/chat.postMessage",
            json={"channel": channel, "text": text},
        )
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result

    async def list_channels(self, limit: int = 100) -> dict[str, Any]:
        """List public channels in the workspace.

        Args:
            limit: Maximum number of channels to return.

        Returns:
            Slack API response with ``channels`` array.
        """
        client = self._ensure_connected()
        resp = await client.get(
            "/conversations.list",
            params={"limit": limit, "types": "public_channel"},
        )
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result

    async def post_file(
        self, channel: str, content: str, filename: str
    ) -> dict[str, Any]:
        """Upload a text snippet to a channel.

        Uses the ``files.upload`` endpoint with ``content`` field.

        Args:
            channel: Target channel ID or name.
            content: File content as a string.
            filename: Display filename.

        Returns:
            Slack API response with the uploaded file metadata.
        """
        client = self._ensure_connected()
        resp = await client.post(
            "/files.upload",
            data={
                "channels": channel,
                "content": content,
                "filename": filename,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result

    async def list_users(self, limit: int = 100) -> dict[str, Any]:
        """List all users in the workspace.

        Args:
            limit: Maximum number of users to return.

        Returns:
            Slack API response with ``members`` array.
        """
        client = self._ensure_connected()
        resp = await client.get("/users.list", params={"limit": limit})
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result
