"""Twilio SMS channel integration."""
from __future__ import annotations

import base64
from typing import Any

import httpx
import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class SMSMessage(BaseModel):
    """An SMS message."""

    sid: str = ""
    from_number: str = ""
    to_number: str = ""
    body: str = ""
    status: str = ""


class SMSChannelConfig(BaseModel):
    """Twilio SMS channel configuration."""

    account_sid: str
    auth_token: str
    from_number: str
    allowed_numbers: list[str] = Field(default_factory=list)
    max_message_length: int = 1600


class TwilioSMSClient:
    """Async Twilio SMS client using httpx."""

    BASE_URL = "https://api.twilio.com/2010-04-01"

    def __init__(self, config: SMSChannelConfig) -> None:
        self._config = config

    def _auth_header(self) -> str:
        """Build HTTP Basic auth header from account credentials."""
        creds = f"{self._config.account_sid}:{self._config.auth_token}"
        return f"Basic {base64.b64encode(creds.encode()).decode()}"

    async def send_message(self, to: str, body: str) -> SMSMessage:
        """Send an SMS message via Twilio REST API."""
        if self._config.allowed_numbers and to not in self._config.allowed_numbers:
            raise ValueError(f"Number {to} not in allowed_numbers list")

        truncated = body[: self._config.max_message_length]

        async with httpx.AsyncClient() as client:
            url = (
                f"{self.BASE_URL}/Accounts/"
                f"{self._config.account_sid}/Messages.json"
            )
            resp = await client.post(
                url,
                headers={"Authorization": self._auth_header()},
                data={
                    "To": to,
                    "From": self._config.from_number,
                    "Body": truncated,
                },
            )
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()

            logger.info(
                "sms_sent",
                to=to,
                sid=data.get("sid", ""),
                status=data.get("status", ""),
            )

            return SMSMessage(
                sid=data.get("sid", ""),
                from_number=data.get("from", self._config.from_number),
                to_number=data.get("to", to),
                body=truncated,
                status=data.get("status", ""),
            )

    @staticmethod
    def parse_incoming_webhook(data: dict[str, Any]) -> SMSMessage:
        """Parse an incoming Twilio webhook payload into an SMSMessage."""
        return SMSMessage(
            sid=data.get("MessageSid", ""),
            from_number=data.get("From", ""),
            to_number=data.get("To", ""),
            body=data.get("Body", ""),
            status=data.get("SmsStatus", ""),
        )
