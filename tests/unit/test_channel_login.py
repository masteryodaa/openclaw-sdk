"""Tests for ChannelManager.login() and request_pairing_code().

Verified against live OpenClaw 2026.2.3-1:
- web.login.start takes NO params (no channel param)
- web.login.wait takes {timeoutMs?} only (no channel param)
- request_pairing_code sends {pairing: true, phone?}
"""

from __future__ import annotations

from openclaw_sdk.channels.manager import ChannelManager
from openclaw_sdk.gateway.mock import MockGateway


def _make_manager() -> tuple[MockGateway, ChannelManager]:
    mock = MockGateway()
    mock._connected = True
    return mock, ChannelManager(mock)


async def test_login_delegates_to_web_login_start() -> None:
    mock, mgr = _make_manager()
    mock.register("web.login.start", {"qrDataUrl": "data:image/png;base64,..."})

    result = await mgr.login()

    method, params = mock.calls[-1]
    assert method == "web.login.start"
    assert params == {}
    assert "qrDataUrl" in result


async def test_login_returns_qr_data() -> None:
    mock, mgr = _make_manager()
    mock.register("web.login.start", {"qrDataUrl": "data:image/png;base64,abc123"})

    result = await mgr.login()

    assert result["qrDataUrl"] == "data:image/png;base64,abc123"


async def test_request_pairing_code_sends_pairing_true() -> None:
    mock, mgr = _make_manager()
    mock.register("web.login.start", {"pairingCode": "1234-5678"})

    result = await mgr.request_pairing_code()

    _, params = mock.calls[-1]
    assert params["pairing"] is True
    assert "phone" not in params
    assert result["pairingCode"] == "1234-5678"


async def test_request_pairing_code_with_phone() -> None:
    mock, mgr = _make_manager()
    mock.register("web.login.start", {"pairingCode": "9999-0000"})

    result = await mgr.request_pairing_code(phone="+15551234567")

    _, params = mock.calls[-1]
    assert params["phone"] == "+15551234567"
    assert params["pairing"] is True
    assert result["pairingCode"] == "9999-0000"
