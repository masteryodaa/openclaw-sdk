from __future__ import annotations

import pytest

from openclaw_sdk.channels.manager import ChannelManager
from openclaw_sdk.gateway.mock import MockGateway

# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


async def test_channel_status(connected_mock_gateway: MockGateway) -> None:
    connected_mock_gateway.register(
        "channels.status",
        {
            "channelOrder": ["whatsapp"],
            "channelLabels": {"whatsapp": "WhatsApp"},
            "channels": {
                "whatsapp": {
                    "configured": False,
                    "linked": False,
                    "authAgeMs": None,
                    "self": {"e164": None, "jid": None},
                    "running": False,
                    "connected": False,
                }
            },
        },
    )
    manager = ChannelManager(connected_mock_gateway)
    result = await manager.status()

    assert "channels" in result
    assert "whatsapp" in result["channels"]
    assert result["channelOrder"] == ["whatsapp"]
    connected_mock_gateway.assert_called_with("channels.status", {})


async def test_channel_status_multiple_channels(connected_mock_gateway: MockGateway) -> None:
    connected_mock_gateway.register(
        "channels.status",
        {
            "channelOrder": ["whatsapp", "telegram"],
            "channels": {
                "whatsapp": {"configured": True, "linked": True},
                "telegram": {"configured": False, "linked": False},
            },
        },
    )
    manager = ChannelManager(connected_mock_gateway)
    result = await manager.status()

    assert len(result["channels"]) == 2
    assert result["channels"]["whatsapp"]["linked"] is True
    assert result["channels"]["telegram"]["linked"] is False


# ---------------------------------------------------------------------------
# logout
# ---------------------------------------------------------------------------


async def test_logout(connected_mock_gateway: MockGateway) -> None:
    connected_mock_gateway.register("channels.logout", {"ok": True})
    manager = ChannelManager(connected_mock_gateway)
    result = await manager.logout("whatsapp")

    assert result is True
    connected_mock_gateway.assert_called_with("channels.logout", {"channel": "whatsapp"})


async def test_logout_passes_channel_name(connected_mock_gateway: MockGateway) -> None:
    connected_mock_gateway.register("channels.logout", {"ok": True})
    manager = ChannelManager(connected_mock_gateway)
    await manager.logout("telegram")
    connected_mock_gateway.assert_called_with("channels.logout", {"channel": "telegram"})


# ---------------------------------------------------------------------------
# web_login_start
# ---------------------------------------------------------------------------


async def test_web_login_start(connected_mock_gateway: MockGateway) -> None:
    connected_mock_gateway.register(
        "web.login.start", {"qrDataUrl": "data:image/png;base64,..."}
    )
    manager = ChannelManager(connected_mock_gateway)
    result = await manager.web_login_start("whatsapp")

    assert "qrDataUrl" in result
    assert result["qrDataUrl"].startswith("data:image/png;base64,")
    connected_mock_gateway.assert_called_with("web.login.start", {"channel": "whatsapp"})


async def test_web_login_start_passes_channel(connected_mock_gateway: MockGateway) -> None:
    connected_mock_gateway.register("web.login.start", {"qrDataUrl": "data:image/png;base64,abc"})
    manager = ChannelManager(connected_mock_gateway)
    await manager.web_login_start("telegram")
    connected_mock_gateway.assert_called_with("web.login.start", {"channel": "telegram"})


# ---------------------------------------------------------------------------
# web_login_wait
# ---------------------------------------------------------------------------


async def test_web_login_wait_default_timeout(connected_mock_gateway: MockGateway) -> None:
    connected_mock_gateway.register(
        "web.login.wait", {"status": "linked", "channel": "whatsapp"}
    )
    manager = ChannelManager(connected_mock_gateway)
    result = await manager.web_login_wait("whatsapp")

    assert result["status"] == "linked"
    connected_mock_gateway.assert_called_with(
        "web.login.wait", {"channel": "whatsapp", "timeoutMs": 120000}
    )


async def test_web_login_wait_custom_timeout(connected_mock_gateway: MockGateway) -> None:
    connected_mock_gateway.register("web.login.wait", {"status": "timeout"})
    manager = ChannelManager(connected_mock_gateway)
    await manager.web_login_wait("whatsapp", timeout_ms=30000)
    connected_mock_gateway.assert_called_with(
        "web.login.wait", {"channel": "whatsapp", "timeoutMs": 30000}
    )


# ---------------------------------------------------------------------------
# error propagation
# ---------------------------------------------------------------------------


async def test_status_raises_on_unregistered_method(connected_mock_gateway: MockGateway) -> None:
    manager = ChannelManager(connected_mock_gateway)
    with pytest.raises(KeyError, match="channels.status"):
        await manager.status()


async def test_raises_when_not_connected(mock_gateway: MockGateway) -> None:
    """Calls against a non-connected gateway raise RuntimeError."""
    mock_gateway.register("channels.status", {"channels": {}})
    manager = ChannelManager(mock_gateway)
    with pytest.raises(RuntimeError, match="not connected"):
        await manager.status()
