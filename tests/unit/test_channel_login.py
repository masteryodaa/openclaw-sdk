"""Tests for ChannelManager.login() and request_pairing_code() additions."""

from __future__ import annotations

from openclaw_sdk.channels.manager import ChannelManager
from openclaw_sdk.gateway.mock import MockGateway


def _make_manager() -> tuple[MockGateway, ChannelManager]:
    mock = MockGateway()
    mock._connected = True
    return mock, ChannelManager(mock)


async def test_login_delegates_to_web_login_start() -> None:
    mock, mgr = _make_manager()
    mock.register("web.login.start", {"qr": "data:image/png;base64,..."})

    result = await mgr.login("whatsapp")

    method, params = mock.calls[-1]
    assert method == "web.login.start"
    assert params["channel"] == "whatsapp"
    assert "qr" in result


async def test_login_works_for_telegram() -> None:
    mock, mgr = _make_manager()
    mock.register("web.login.start", {"status": "pending"})

    result = await mgr.login("telegram")

    _, params = mock.calls[-1]
    assert params["channel"] == "telegram"
    assert result["status"] == "pending"


async def test_request_pairing_code_sends_pairing_true() -> None:
    mock, mgr = _make_manager()
    mock.register("web.login.start", {"pairingCode": "1234-5678"})

    result = await mgr.request_pairing_code("whatsapp")

    _, params = mock.calls[-1]
    assert params["channel"] == "whatsapp"
    assert params["pairing"] is True
    assert "phone" not in params
    assert result["pairingCode"] == "1234-5678"


async def test_request_pairing_code_with_phone() -> None:
    mock, mgr = _make_manager()
    mock.register("web.login.start", {"pairingCode": "9999-0000"})

    result = await mgr.request_pairing_code("whatsapp", phone="+15551234567")

    _, params = mock.calls[-1]
    assert params["phone"] == "+15551234567"
    assert params["pairing"] is True
    assert result["pairingCode"] == "9999-0000"
