"""Tests for gateway/local.py — LocalGateway."""
from __future__ import annotations

import pytest

from openclaw_sdk.core.types import HealthStatus, StreamEvent
from openclaw_sdk.core.constants import EventType
from openclaw_sdk.gateway.local import LocalGateway, DEFAULT_WS_URL
from openclaw_sdk.gateway.mock import MockGateway


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_local_with_mock() -> tuple[LocalGateway, MockGateway]:
    """Create a LocalGateway with a MockGateway injected as the inner."""
    gw = LocalGateway()
    mock = MockGateway()
    await mock.connect()
    gw._inner = mock
    return gw, mock


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


def test_default_ws_url() -> None:
    gw = LocalGateway()
    assert gw._ws_url == DEFAULT_WS_URL
    assert gw._ws_url == "ws://127.0.0.1:18789/gateway"


def test_custom_ws_url() -> None:
    gw = LocalGateway(ws_url="ws://localhost:9999/gw")
    assert gw._ws_url == "ws://localhost:9999/gw"


def test_inner_starts_none() -> None:
    gw = LocalGateway()
    assert gw._inner is None


# ---------------------------------------------------------------------------
# health() — before connect (no inner)
# ---------------------------------------------------------------------------


async def test_health_not_connected_returns_unhealthy() -> None:
    gw = LocalGateway()
    status = await gw.health()
    assert isinstance(status, HealthStatus)
    assert status.healthy is False


# ---------------------------------------------------------------------------
# health() — delegates to inner
# ---------------------------------------------------------------------------


async def test_health_delegates_to_inner() -> None:
    gw, mock = await _make_local_with_mock()
    status = await gw.health()
    assert status.healthy is True  # MockGateway reports healthy when connected


# ---------------------------------------------------------------------------
# call() — not connected raises RuntimeError
# ---------------------------------------------------------------------------


async def test_call_not_connected_raises() -> None:
    gw = LocalGateway()
    with pytest.raises(RuntimeError, match="not connected"):
        await gw.call("sessions.list", {})


# ---------------------------------------------------------------------------
# call() — delegates to inner
# ---------------------------------------------------------------------------


async def test_call_delegates_to_inner() -> None:
    gw, mock = await _make_local_with_mock()
    mock.register("test.method", {"result": "ok"})
    result = await gw.call("test.method", {})
    assert result == {"result": "ok"}


async def test_call_passes_params_to_inner() -> None:
    gw, mock = await _make_local_with_mock()
    received_params: dict = {}

    def handler(params):
        received_params.update(params or {})
        return {"echo": params}

    mock.register("echo.method", handler)
    result = await gw.call("echo.method", {"foo": "bar"})
    assert result == {"echo": {"foo": "bar"}}
    assert received_params == {"foo": "bar"}


# ---------------------------------------------------------------------------
# subscribe() — not connected raises RuntimeError
# ---------------------------------------------------------------------------


async def test_subscribe_not_connected_raises() -> None:
    gw = LocalGateway()
    with pytest.raises(RuntimeError, match="not connected"):
        await gw.subscribe()


# ---------------------------------------------------------------------------
# subscribe() — delegates to inner
# ---------------------------------------------------------------------------


async def test_subscribe_delegates_to_inner() -> None:
    gw, mock = await _make_local_with_mock()
    # Emit an event then close stream
    mock.emit_event(StreamEvent(event_type=EventType.DONE, data={"payload": {}}))
    mock.close_stream()

    subscriber = await gw.subscribe()
    events = []
    async for event in subscriber:
        events.append(event)

    assert len(events) == 1
    assert events[0].event_type == EventType.DONE


# ---------------------------------------------------------------------------
# close() — when inner is None (no-op)
# ---------------------------------------------------------------------------


async def test_close_when_not_connected_is_noop() -> None:
    gw = LocalGateway()
    # Should not raise
    await gw.close()
    assert gw._inner is None


# ---------------------------------------------------------------------------
# close() — delegates to inner and disconnects
# ---------------------------------------------------------------------------


async def test_close_delegates_to_inner() -> None:
    gw, mock = await _make_local_with_mock()
    assert mock._connected is True
    await gw.close()
    assert mock._connected is False


# ---------------------------------------------------------------------------
# connect() — injects ProtocolGateway (mocking _open_connection)
# ---------------------------------------------------------------------------


async def test_connect_creates_protocol_gateway_inner() -> None:
    """connect() should set _inner to a ProtocolGateway instance.

    We mock the actual WebSocket open so no real network call is made.
    """
    import unittest.mock as mock_lib
    from openclaw_sdk.gateway.protocol import ProtocolGateway

    gw = LocalGateway()

    async def fake_connect(self) -> None:
        # Simulate a successful connect without a real WS
        self._connected = True

    with mock_lib.patch.object(ProtocolGateway, "connect", fake_connect):
        await gw.connect()

    assert gw._inner is not None
    assert isinstance(gw._inner, ProtocolGateway)
