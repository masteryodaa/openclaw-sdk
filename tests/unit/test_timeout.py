"""Tests for per-call timeout on gateway.call()."""
from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from openclaw_sdk.core.exceptions import TimeoutError as OCTimeoutError
from openclaw_sdk.gateway.mock import MockGateway
from openclaw_sdk.gateway.protocol import ProtocolGateway


# ------------------------------------------------------------------ #
# Helpers (same as test_protocol_gateway.py)
# ------------------------------------------------------------------ #


def _challenge(nonce: str = "test-nonce", ts: int = 1000) -> str:
    return json.dumps(
        {
            "type": "event",
            "event": "connect.challenge",
            "payload": {"nonce": nonce, "ts": ts},
        }
    )


def _connect_ok(req_id: str) -> str:
    return json.dumps({
        "type": "res",
        "id": req_id,
        "ok": True,
        "payload": {
            "type": "hello-ok",
            "protocol": 3,
            "server": {"version": "test", "host": "test"},
        },
    })


def _result(req_id: str, result: dict[str, Any]) -> str:
    return json.dumps({"type": "res", "id": req_id, "ok": True, "payload": result})


class QueueWebSocket:
    """A FakeWebSocket that reads from an asyncio.Queue for dynamic scenarios."""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._sent: list[str] = []
        self.closed = False
        self._on_send: list[Any] = []

    async def put(self, msg: str) -> None:
        await self._queue.put(msg)

    def put_nowait(self, msg: str) -> None:
        self._queue.put_nowait(msg)

    async def send(self, data: str) -> None:
        self._sent.append(data)
        for callback in self._on_send:
            await callback(data)

    async def close(self) -> None:
        self.closed = True
        self._queue.put_nowait("")

    def __aiter__(self) -> Any:
        return self._iter()

    async def _iter(self) -> Any:
        while True:
            msg = await self._queue.get()
            if msg == "":
                break
            yield msg


_FAKE_DEVICE = {
    "version": 1,
    "deviceId": "deadbeef",
    "publicKeyPem": (
        "-----BEGIN PUBLIC KEY-----\n"
        "MCowBQYDK2VwAyEANfoKedj4nS7zRIvgFUpZTJGF0LEuGgvRQRhCkJsZ6mg=\n"
        "-----END PUBLIC KEY-----\n"
    ),
    "privateKeyPem": (
        "-----BEGIN PRIVATE KEY-----\n"
        "MC4CAQAwBQYDK2VwBCIEIM1Vw97UWQOJQVnSF/upfZPPPgqp8yp5mUknqhnSiajw\n"
        "-----END PRIVATE KEY-----\n"
    ),
    "createdAtMs": 1000,
}

_FAKE_DEVICE_AUTH = {
    "version": 1,
    "deviceId": "deadbeef",
    "tokens": {
        "operator": {
            "token": "test-token-123",
            "role": "operator",
            "scopes": ["operator.admin"],
        }
    },
}


def _patch_open(ws: Any) -> Any:
    return patch(
        "openclaw_sdk.gateway.protocol._open_connection",
        new=AsyncMock(return_value=ws),
    )


def _patch_device() -> Any:
    return patch.multiple(
        "openclaw_sdk.gateway.protocol",
        _load_device_identity=lambda: _FAKE_DEVICE,
        _load_device_auth=lambda: _FAKE_DEVICE_AUTH,
    )


def _auto_respond_connect(ws: QueueWebSocket) -> None:
    async def _respond(data: str) -> None:
        parsed = json.loads(data)
        if parsed.get("method") == "connect":
            ws.put_nowait(_connect_ok(parsed["id"]))

    ws._on_send.append(_respond)


# ------------------------------------------------------------------ #
# Tests: per-call timeout on ProtocolGateway.call()
# ------------------------------------------------------------------ #


async def test_call_timeout_raises() -> None:
    """call() raises OCTimeoutError when the gateway never responds."""
    ws = QueueWebSocket()
    ws.put_nowait(_challenge())
    _auto_respond_connect(ws)

    # Only respond to connect, never to sessions.list
    with _patch_open(ws), _patch_device():
        gw = ProtocolGateway(ws_url="ws://localhost:18789/gateway", token="tok")
        await gw.connect()

        with pytest.raises(OCTimeoutError, match="timed out after 0.05s"):
            await gw.call("sessions.list", {}, timeout=0.05)

        await gw.close()


async def test_call_default_timeout() -> None:
    """ProtocolGateway uses default_timeout when no per-call timeout is given."""
    ws = QueueWebSocket()
    ws.put_nowait(_challenge())
    _auto_respond_connect(ws)

    with _patch_open(ws), _patch_device():
        gw = ProtocolGateway(
            ws_url="ws://localhost:18789/gateway",
            token="tok",
            default_timeout=0.05,
        )
        await gw.connect()

        # No per-call timeout => uses default_timeout of 0.05s
        with pytest.raises(OCTimeoutError, match="timed out after 0.05s"):
            await gw.call("sessions.list", {})

        await gw.close()


async def test_call_explicit_timeout_overrides_default() -> None:
    """An explicit per-call timeout takes precedence over default_timeout."""
    ws = QueueWebSocket()
    ws.put_nowait(_challenge())
    _auto_respond_connect(ws)

    with _patch_open(ws), _patch_device():
        gw = ProtocolGateway(
            ws_url="ws://localhost:18789/gateway",
            token="tok",
            default_timeout=60.0,  # large default
        )
        await gw.connect()

        # Use a small per-call timeout that will trigger
        with pytest.raises(OCTimeoutError, match="timed out after 0.05s"):
            await gw.call("sessions.list", {}, timeout=0.05)

        await gw.close()


async def test_call_succeeds_within_timeout() -> None:
    """call() returns normally when the gateway responds within timeout."""
    ws = QueueWebSocket()
    ws.put_nowait(_challenge())

    async def _respond(data: str) -> None:
        parsed = json.loads(data)
        if parsed.get("method") == "connect":
            ws.put_nowait(_connect_ok(parsed["id"]))
        elif "method" in parsed:
            ws.put_nowait(_result(parsed["id"], {"sessions": []}))

    ws._on_send.append(_respond)

    with _patch_open(ws), _patch_device():
        gw = ProtocolGateway(ws_url="ws://localhost:18789/gateway", token="tok")
        await gw.connect()
        result = await gw.call("sessions.list", {}, timeout=5.0)
        await gw.close()

    assert result == {"sessions": []}


async def test_timeout_error_is_openclaw_error() -> None:
    """OCTimeoutError is a subclass of OpenClawError."""
    from openclaw_sdk.core.exceptions import OpenClawError

    err = OCTimeoutError("test timeout")
    assert isinstance(err, OpenClawError)


# ------------------------------------------------------------------ #
# Tests: MockGateway accepts timeout kwarg
# ------------------------------------------------------------------ #


async def test_mock_accepts_timeout() -> None:
    """MockGateway.call() accepts timeout keyword arg without error."""
    mock = MockGateway()
    await mock.connect()
    mock.register("sessions.list", {"sessions": []})

    result = await mock.call("sessions.list", {}, timeout=5.0)
    assert result == {"sessions": []}

    await mock.close()


async def test_mock_ignores_timeout_value() -> None:
    """MockGateway ignores the timeout value — it is for API compatibility only."""
    mock = MockGateway()
    await mock.connect()
    mock.register("test.method", {"ok": True})

    # Should not raise even with very small timeout
    result = await mock.call("test.method", timeout=0.001)
    assert result == {"ok": True}

    await mock.close()
