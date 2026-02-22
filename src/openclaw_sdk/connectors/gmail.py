"""Gmail connector — send, list, and read emails."""

from __future__ import annotations

import base64
from email.mime.text import MIMEText
from typing import Any

import structlog

from openclaw_sdk.connectors.base import Connector, ConnectorAction, ConnectorConfig

logger = structlog.get_logger(__name__)


class GmailConnector(Connector):
    """Connector for the Gmail API v1.

    Expects an OAuth2 access token passed as ``api_key``.

    Usage::

        config = ConnectorConfig(api_key="ya29.xxx")
        async with GmailConnector(config) as gmail:
            await gmail.send_email("user@example.com", "Hello", "Body text")
    """

    DEFAULT_BASE_URL = "https://gmail.googleapis.com/gmail/v1"

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
                name="send_email",
                description="Send an email via Gmail",
                required_params=["to", "subject", "body"],
            ),
            ConnectorAction(
                name="list_messages",
                description="List messages matching a query",
                optional_params=["query", "max_results"],
            ),
            ConnectorAction(
                name="get_message",
                description="Get a single message by ID",
                required_params=["message_id"],
            ),
        ]

    @staticmethod
    def _encode_message(to: str, subject: str, body: str) -> str:
        """Build a base64url-encoded RFC 2822 message.

        Args:
            to: Recipient email address.
            subject: Email subject line.
            body: Plain-text email body.

        Returns:
            Base64url-encoded message string.
        """
        msg = MIMEText(body)
        msg["to"] = to
        msg["subject"] = subject
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
        return raw

    async def send_email(
        self, to: str, subject: str, body: str
    ) -> dict[str, Any]:
        """Send an email via Gmail.

        Args:
            to: Recipient email address.
            subject: Email subject line.
            body: Plain-text email body.

        Returns:
            API response with sent message metadata.
        """
        client = self._ensure_connected()
        raw = self._encode_message(to, subject, body)
        resp = await client.post(
            "/users/me/messages/send",
            json={"raw": raw},
        )
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result

    async def list_messages(
        self, query: str = "", max_results: int = 10
    ) -> dict[str, Any]:
        """List messages matching a Gmail search query.

        Args:
            query: Gmail search query (e.g. ``"from:user@example.com"``).
            max_results: Maximum number of messages to return.

        Returns:
            API response with ``messages`` array of ``{id, threadId}``.
        """
        client = self._ensure_connected()
        params: dict[str, Any] = {"maxResults": max_results}
        if query:
            params["q"] = query
        resp = await client.get("/users/me/messages", params=params)
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result

    async def get_message(self, message_id: str) -> dict[str, Any]:
        """Get a single message by ID.

        Args:
            message_id: The Gmail message ID.

        Returns:
            Full message object including headers, body, and metadata.
        """
        client = self._ensure_connected()
        resp = await client.get(f"/users/me/messages/{message_id}")
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result
