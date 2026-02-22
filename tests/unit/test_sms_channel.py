"""Tests for SMS channel integration."""
from __future__ import annotations

import base64
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from openclaw_sdk.channels.sms import (
    SMSChannelConfig,
    SMSMessage,
    TwilioSMSClient,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(**overrides: Any) -> SMSChannelConfig:
    defaults: dict[str, Any] = {
        "account_sid": "ACtest123",
        "auth_token": "token456",
        "from_number": "+15551234567",
    }
    defaults.update(overrides)
    return SMSChannelConfig(**defaults)


def _mock_twilio_response(
    sid: str = "SM123",
    status: str = "queued",
    to: str = "+15559876543",
    from_: str = "+15551234567",
) -> httpx.Response:
    """Build a fake httpx.Response mimicking the Twilio Messages API."""
    return httpx.Response(
        status_code=201,
        json={"sid": sid, "status": status, "to": to, "from": from_},
        request=httpx.Request("POST", "https://api.twilio.com/fake"),
    )


# ---------------------------------------------------------------------------
# test_sms_message_model
# ---------------------------------------------------------------------------


def test_sms_message_model() -> None:
    """SMSMessage defaults are empty strings."""
    msg = SMSMessage()
    assert msg.sid == ""
    assert msg.from_number == ""
    assert msg.to_number == ""
    assert msg.body == ""
    assert msg.status == ""

    msg2 = SMSMessage(
        sid="SM1", from_number="+1", to_number="+2", body="hi", status="sent"
    )
    assert msg2.sid == "SM1"
    assert msg2.body == "hi"


# ---------------------------------------------------------------------------
# test_sms_config_validation
# ---------------------------------------------------------------------------


def test_sms_config_validation() -> None:
    """SMSChannelConfig requires account_sid, auth_token, from_number."""
    cfg = _make_config()
    assert cfg.account_sid == "ACtest123"
    assert cfg.auth_token == "token456"
    assert cfg.from_number == "+15551234567"
    assert cfg.allowed_numbers == []
    assert cfg.max_message_length == 1600

    with pytest.raises(Exception):  # noqa: B017
        SMSChannelConfig()  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# test_auth_header_format
# ---------------------------------------------------------------------------


def test_auth_header_format() -> None:
    """Auth header is HTTP Basic with base64-encoded sid:token."""
    cfg = _make_config()
    client = TwilioSMSClient(cfg)
    header = client._auth_header()

    expected_creds = base64.b64encode(b"ACtest123:token456").decode()
    assert header == f"Basic {expected_creds}"
    assert header.startswith("Basic ")


# ---------------------------------------------------------------------------
# test_send_message_success
# ---------------------------------------------------------------------------


async def test_send_message_success() -> None:
    """send_message posts to Twilio and returns an SMSMessage on success."""
    cfg = _make_config()
    client = TwilioSMSClient(cfg)
    fake_resp = _mock_twilio_response()

    mock_post = AsyncMock(return_value=fake_resp)

    with patch("openclaw_sdk.channels.sms.httpx.AsyncClient") as mock_cls:
        instance = AsyncMock()
        instance.post = mock_post
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = instance

        result = await client.send_message("+15559876543", "Hello!")

    assert isinstance(result, SMSMessage)
    assert result.sid == "SM123"
    assert result.status == "queued"
    assert result.body == "Hello!"
    assert result.to_number == "+15559876543"

    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args
    assert call_kwargs.kwargs["data"]["To"] == "+15559876543"
    assert call_kwargs.kwargs["data"]["From"] == "+15551234567"
    assert call_kwargs.kwargs["data"]["Body"] == "Hello!"


# ---------------------------------------------------------------------------
# test_send_message_truncates_long_body
# ---------------------------------------------------------------------------


async def test_send_message_truncates_long_body() -> None:
    """Messages longer than max_message_length are truncated."""
    cfg = _make_config(max_message_length=10)
    client = TwilioSMSClient(cfg)
    fake_resp = _mock_twilio_response()

    with patch("openclaw_sdk.channels.sms.httpx.AsyncClient") as mock_cls:
        instance = AsyncMock()
        instance.post = AsyncMock(return_value=fake_resp)
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = instance

        result = await client.send_message("+15559876543", "A" * 100)

    assert result.body == "A" * 10
    call_kwargs = instance.post.call_args
    assert call_kwargs.kwargs["data"]["Body"] == "A" * 10


# ---------------------------------------------------------------------------
# test_send_message_allowed_numbers_enforced
# ---------------------------------------------------------------------------


async def test_send_message_allowed_numbers_enforced() -> None:
    """Sending to a number not in allowed_numbers raises ValueError."""
    cfg = _make_config(allowed_numbers=["+15550001111"])
    client = TwilioSMSClient(cfg)

    with pytest.raises(ValueError, match="not in allowed_numbers"):
        await client.send_message("+15559999999", "blocked")


# ---------------------------------------------------------------------------
# test_send_message_allowed_numbers_empty_allows_all
# ---------------------------------------------------------------------------


async def test_send_message_allowed_numbers_empty_allows_all() -> None:
    """When allowed_numbers is empty, any number is permitted."""
    cfg = _make_config(allowed_numbers=[])
    client = TwilioSMSClient(cfg)
    fake_resp = _mock_twilio_response(to="+15559999999")

    with patch("openclaw_sdk.channels.sms.httpx.AsyncClient") as mock_cls:
        instance = AsyncMock()
        instance.post = AsyncMock(return_value=fake_resp)
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = instance

        result = await client.send_message("+15559999999", "hello")

    assert result.to_number == "+15559999999"


# ---------------------------------------------------------------------------
# test_parse_incoming_webhook
# ---------------------------------------------------------------------------


def test_parse_incoming_webhook() -> None:
    """parse_incoming_webhook maps Twilio webhook fields to SMSMessage."""
    payload: dict[str, str] = {
        "MessageSid": "SM999",
        "From": "+15551112222",
        "To": "+15553334444",
        "Body": "Incoming text",
        "SmsStatus": "received",
    }

    msg = TwilioSMSClient.parse_incoming_webhook(payload)

    assert msg.sid == "SM999"
    assert msg.from_number == "+15551112222"
    assert msg.to_number == "+15553334444"
    assert msg.body == "Incoming text"
    assert msg.status == "received"
