"""Unit tests for ProtocolGateway — no live server required.

All WebSocket I/O is mocked via ``_open_connection`` so these tests run offline.
"""
from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from openclaw_sdk.core.exceptions import GatewayError
from openclaw_sdk.core.types import StreamEvent
from openclaw_sdk.gateway.protocol import ProtocolGateway, _load_token


# ------------------------------------------------------------------ #
# Helpers — build fake WebSocket messages
# ------------------------------------------------------------------ #


def _challenge(nonce: str = "test-nonce", ts: int = 1000) -> str:
    return json.dumps(
        {
            "type": "event",
            "event": "connect.challenge",
            "payload": {"nonce": nonce, "ts": ts},
        }
    )


def _result(req_id: str, result: dict[str, Any]) -> str:
    return json.dumps({"id": req_id, "result": result})


def _error(req_id: str, code: int, message: str) -> str:
    return json.dumps({"id": req_id, "error": {"code": code, "message": message}})


def _event(name: str, payload: dict[str, Any]) -> str:
    return json.dumps({"type": "event", "event": name, "payload": payload})


# ------------------------------------------------------------------ #
# FakeWebSocket — async iterable that yields a fixed message list
# ------------------------------------------------------------------ #


class FakeWebSocket:
    """Minimal WebSocket double that yields messages from a list."""

    def __init__(self, messages: list[str]) -> None:
        self._messages = list(messages)
        self._sent: list[str] = []
        self.closed = False

    async def send(self, data: str) -> None:
        self._sent.append(data)

    async def close(self) -> None:
        self.closed = True

    def __aiter__(self) -> AsyncIterator[str]:
        return self._iter()

    async def _iter(self) -> AsyncIterator[str]:
        for msg in self._messages:
            yield msg


class QueueWebSocket:
    """A FakeWebSocket that reads from an asyncio.Queue for dynamic scenarios."""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._sent: list[str] = []
        self.closed = False
        self._on_send: list[Any] = []  # list[Callable[[str], Awaitable[None]]]

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
        self._queue.put_nowait("")  # Unblock the iterator

    def __aiter__(self) -> AsyncIterator[str]:
        return self._iter()

    async def _iter(self) -> AsyncIterator[str]:
        while True:
            msg = await self._queue.get()
            if msg == "":
                break
            yield msg


# ------------------------------------------------------------------ #
# Convenience: build a gateway whose _open_connection is patched
# ------------------------------------------------------------------ #


def _patch_open(ws: Any) -> Any:
    """Return a context-manager patch for _open_connection that returns *ws*."""
    return patch(
        "openclaw_sdk.gateway.protocol._open_connection",
        new=AsyncMock(return_value=ws),
    )


# ------------------------------------------------------------------ #
# Tests: _load_token
# ------------------------------------------------------------------ #


def test_load_token_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENCLAW_GATEWAY_TOKEN", "env-token-xyz")
    assert _load_token() == "env-token-xyz"


def test_load_token_returns_none_when_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    monkeypatch.delenv("OPENCLAW_GATEWAY_TOKEN", raising=False)
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    result = _load_token()
    assert result is None


def test_load_token_from_json(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    monkeypatch.delenv("OPENCLAW_GATEWAY_TOKEN", raising=False)
    cfg_dir = tmp_path / ".openclaw"
    cfg_dir.mkdir()
    (cfg_dir / "openclaw.json").write_text(
        json.dumps({"gateway": {"auth": {"token": "file-token-abc"}}})
    )
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    assert _load_token() == "file-token-abc"


# ------------------------------------------------------------------ #
# Tests: connect + challenge handling
# ------------------------------------------------------------------ #


@pytest.mark.asyncio
async def test_connect_handles_challenge() -> None:
    """Gateway must complete handshake when connect.challenge is received."""
    ws = FakeWebSocket([_challenge()])

    with _patch_open(ws):
        gw = ProtocolGateway(ws_url="ws://localhost:18789/gateway", token="tok")
        await gw.connect()

    assert gw._connected is True
    # An auth message must have been sent
    assert len(ws._sent) == 1
    sent = json.loads(ws._sent[0])
    assert sent["type"] == "auth"
    assert sent["token"] == "tok"
    assert sent["nonce"] == "test-nonce"

    await gw.close()


@pytest.mark.asyncio
async def test_connect_no_token_skips_auth() -> None:
    """When no token is configured, no auth message is sent."""
    ws = FakeWebSocket([_challenge()])

    with _patch_open(ws):
        with patch("openclaw_sdk.gateway.protocol._load_token", return_value=None):
            gw = ProtocolGateway(ws_url="ws://localhost:18789/gateway", token=None)
            await gw.connect()

    assert gw._connected is True
    assert ws._sent == []  # no auth sent

    await gw.close()


@pytest.mark.asyncio
async def test_connect_timeout_if_no_challenge() -> None:
    """If no connect.challenge arrives, connect() raises GatewayError."""
    ws = FakeWebSocket([])  # server sends nothing

    with _patch_open(ws):
        gw = ProtocolGateway(
            ws_url="ws://localhost:18789/gateway",
            token="tok",
            connect_timeout=0.05,
        )
        with pytest.raises(GatewayError, match="Timed out"):
            await gw.connect()


# ------------------------------------------------------------------ #
# Tests: call / response correlation
# ------------------------------------------------------------------ #


@pytest.mark.asyncio
async def test_call_returns_result() -> None:
    """call() sends a request and returns the correlated result dict."""
    ws = QueueWebSocket()
    ws.put_nowait(_challenge())

    async def _respond(data: str) -> None:
        parsed = json.loads(data)
        if "method" in parsed:
            ws.put_nowait(_result(parsed["id"], {"sessions": []}))

    ws._on_send.append(_respond)

    with _patch_open(ws):
        gw = ProtocolGateway(ws_url="ws://localhost:18789/gateway", token="tok")
        await gw.connect()
        result = await gw.call("sessions.list", {})
        await gw.close()

    assert result == {"sessions": []}


@pytest.mark.asyncio
async def test_call_raises_on_error_response() -> None:
    """call() raises GatewayError when the gateway returns an error envelope."""
    ws = QueueWebSocket()
    ws.put_nowait(_challenge())

    async def _respond(data: str) -> None:
        parsed = json.loads(data)
        if "method" in parsed:
            ws.put_nowait(
                _error(parsed["id"], 400, "invalid sessions.list params: bad")
            )

    ws._on_send.append(_respond)

    with _patch_open(ws):
        gw = ProtocolGateway(ws_url="ws://localhost:18789/gateway", token="tok")
        await gw.connect()
        with pytest.raises(GatewayError, match="invalid sessions.list params"):
            await gw.call("sessions.list", {})
        await gw.close()


@pytest.mark.asyncio
async def test_call_raises_when_not_connected() -> None:
    """call() raises GatewayError if connect() was never called."""
    gw = ProtocolGateway(ws_url="ws://localhost:18789/gateway", token="tok")
    with pytest.raises(GatewayError, match="Not connected"):
        await gw.call("sessions.list", {})


@pytest.mark.asyncio
async def test_call_passes_idempotency_key() -> None:
    """call() embeds idempotency_key as idempotencyKey inside the params."""
    ws = QueueWebSocket()
    ws.put_nowait(_challenge())
    captured_params: list[dict[str, Any]] = []

    async def _respond(data: str) -> None:
        parsed = json.loads(data)
        if "method" in parsed:
            captured_params.append(parsed.get("params", {}))
            ws.put_nowait(_result(parsed["id"], {"runId": "r1"}))

    ws._on_send.append(_respond)

    with _patch_open(ws):
        gw = ProtocolGateway(ws_url="ws://localhost:18789/gateway", token="tok")
        await gw.connect()
        await gw.call(
            "chat.send",
            {"sessionKey": "agent:main:main", "message": "hi"},
            idempotency_key="idem-123",
        )
        await gw.close()

    assert captured_params[0]["idempotencyKey"] == "idem-123"


@pytest.mark.asyncio
async def test_call_multiple_requests_correlated() -> None:
    """Multiple in-flight calls are each resolved by their own request id."""
    ws = QueueWebSocket()
    ws.put_nowait(_challenge())
    sent_requests: list[dict[str, Any]] = []

    async def _respond(data: str) -> None:
        parsed = json.loads(data)
        if "method" in parsed:
            sent_requests.append(parsed)

    ws._on_send.append(_respond)

    with _patch_open(ws):
        gw = ProtocolGateway(ws_url="ws://localhost:18789/gateway", token="tok")
        await gw.connect()

        # Fire two requests in parallel
        task_a = asyncio.create_task(gw.call("sessions.list", {}))
        task_b = asyncio.create_task(gw.call("cron.list", {}))

        # Give the event loop a chance to send both requests
        await asyncio.sleep(0.01)

        # Now inject results in reverse order
        assert len(sent_requests) == 2
        id_a = sent_requests[0]["id"]
        id_b = sent_requests[1]["id"]
        ws.put_nowait(_result(id_b, {"jobs": []}))
        ws.put_nowait(_result(id_a, {"sessions": []}))

        result_a = await task_a
        result_b = await task_b
        await gw.close()

    assert result_a == {"sessions": []}
    assert result_b == {"jobs": []}


# ------------------------------------------------------------------ #
# Tests: disconnect fails in-flight requests
# ------------------------------------------------------------------ #


@pytest.mark.asyncio
async def test_inflight_requests_fail_on_close() -> None:
    """In-flight calls get GatewayError when close() is called."""
    ws = QueueWebSocket()
    ws.put_nowait(_challenge())

    # _respond intentionally does nothing — no response ever arrives

    with _patch_open(ws):
        gw = ProtocolGateway(ws_url="ws://localhost:18789/gateway", token="tok")
        await gw.connect()

        call_task = asyncio.create_task(gw.call("sessions.list", {}))
        await asyncio.sleep(0.01)  # Let the request register in _pending

        await gw.close()

        with pytest.raises(GatewayError):
            await call_task


# ------------------------------------------------------------------ #
# Tests: subscribe / event routing
# ------------------------------------------------------------------ #


@pytest.mark.asyncio
async def test_subscribe_receives_push_events() -> None:
    """Push events from the gateway are yielded by subscribe()."""
    ws = QueueWebSocket()
    ws.put_nowait(_challenge())
    # Note: events are queued AFTER subscribe() registers the subscriber,
    # so we add them after connect() via a short-delay task.

    received: list[StreamEvent] = []

    with _patch_open(ws):
        gw = ProtocolGateway(ws_url="ws://localhost:18789/gateway", token="tok")
        await gw.connect()
        stream = await gw.subscribe()

        # Now inject the events — subscriber is registered
        ws.put_nowait(_event("task.done", {"runId": "r1", "status": "done"}))
        ws.put_nowait(_event("task.progress", {"percent": 50}))

        async def _collect() -> None:
            count = 0
            async for ev in stream:
                received.append(ev)
                count += 1
                if count >= 2:
                    break

        collect_task = asyncio.create_task(_collect())
        await asyncio.sleep(0.05)
        await gw.close()
        try:
            await asyncio.wait_for(collect_task, timeout=1.0)
        except asyncio.TimeoutError:
            collect_task.cancel()

    assert len(received) == 2
    assert received[0].data["event"] == "task.done"
    assert received[1].data["event"] == "task.progress"


@pytest.mark.asyncio
async def test_subscribe_filters_event_types() -> None:
    """subscribe(event_types=[...]) only yields matching events."""
    ws = QueueWebSocket()
    ws.put_nowait(_challenge())

    received: list[StreamEvent] = []

    with _patch_open(ws):
        gw = ProtocolGateway(ws_url="ws://localhost:18789/gateway", token="tok")
        await gw.connect()
        stream = await gw.subscribe(event_types=["task.done"])

        # Now inject events — subscriber is registered
        ws.put_nowait(_event("task.done", {"runId": "r1"}))
        ws.put_nowait(_event("task.progress", {"percent": 50}))

        async def _collect() -> None:
            async for ev in stream:
                received.append(ev)
                break  # stop after one

        collect_task = asyncio.create_task(_collect())
        await asyncio.sleep(0.05)
        await gw.close()
        try:
            await asyncio.wait_for(collect_task, timeout=1.0)
        except asyncio.TimeoutError:
            collect_task.cancel()

    assert len(received) == 1
    assert received[0].data["event"] == "task.done"


@pytest.mark.asyncio
async def test_subscribe_raises_when_not_connected() -> None:
    gw = ProtocolGateway(ws_url="ws://localhost:18789/gateway", token="tok")
    with pytest.raises(GatewayError, match="Not connected"):
        await gw.subscribe()


# ------------------------------------------------------------------ #
# Tests: context manager
# ------------------------------------------------------------------ #


@pytest.mark.asyncio
async def test_context_manager_connects_and_closes() -> None:
    """async with ProtocolGateway(...) calls connect() and close()."""
    ws = FakeWebSocket([_challenge()])

    with _patch_open(ws):
        gw = ProtocolGateway(ws_url="ws://localhost:18789/gateway", token="tok")
        async with gw:
            assert gw._connected is True
    assert gw._connected is False


# ------------------------------------------------------------------ #
# Tests: request ID generation
# ------------------------------------------------------------------ #


def test_next_id_increments() -> None:
    gw = ProtocolGateway(ws_url="ws://localhost:18789/gateway", token="tok")
    assert gw._next_id() == "req_1"
    assert gw._next_id() == "req_2"
    assert gw._next_id() == "req_3"


# ------------------------------------------------------------------ #
# Tests: health()
# ------------------------------------------------------------------ #


@pytest.mark.asyncio
async def test_health_returns_false_when_not_connected() -> None:
    gw = ProtocolGateway(ws_url="ws://localhost:18789/gateway", token="tok")
    status = await gw.health()
    assert status.healthy is False


@pytest.mark.asyncio
async def test_health_returns_true_on_success() -> None:
    """health() calls system-presence and returns a healthy HealthStatus."""
    ws = QueueWebSocket()
    ws.put_nowait(_challenge())

    async def _respond(data: str) -> None:
        parsed = json.loads(data)
        if parsed.get("method") == "system-presence":
            ws.put_nowait(_result(parsed["id"], {"version": "2026.2.3-1"}))

    ws._on_send.append(_respond)

    with _patch_open(ws):
        gw = ProtocolGateway(ws_url="ws://localhost:18789/gateway", token="tok")
        await gw.connect()
        status = await gw.health()
        await gw.close()

    assert status.healthy is True
    assert status.latency_ms is not None
    assert status.latency_ms >= 0


# ------------------------------------------------------------------ #
# Tests: reconnect / backoff
# ------------------------------------------------------------------ #


@pytest.mark.asyncio
async def test_connect_retries_on_os_error() -> None:
    """connect() retries with backoff when _open_connection raises OSError."""
    attempt_count = 0
    ws = FakeWebSocket([_challenge()])

    async def _fake_open(url: str, timeout: float) -> Any:
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise OSError("connection refused")
        return ws

    with patch("openclaw_sdk.gateway.protocol._open_connection", new=_fake_open):
        with patch(
            "asyncio.sleep", new_callable=AsyncMock
        ):  # skip actual sleeps
            gw = ProtocolGateway(ws_url="ws://localhost:18789/gateway", token="tok")
            await gw.connect()

    assert attempt_count == 3
    assert gw._connected is True
    await gw.close()


# ------------------------------------------------------------------ #
# Tests: close() is idempotent / safe when not connected
# ------------------------------------------------------------------ #


@pytest.mark.asyncio
async def test_close_when_not_connected() -> None:
    """close() must not raise even when connect() was never called."""
    gw = ProtocolGateway(ws_url="ws://localhost:18789/gateway", token="tok")
    await gw.close()
    assert gw._connected is False


@pytest.mark.asyncio
async def test_double_connect_is_noop() -> None:
    """Calling connect() twice when already connected is a no-op."""
    ws = FakeWebSocket([_challenge()])

    with _patch_open(ws) as mock_open:
        gw = ProtocolGateway(ws_url="ws://localhost:18789/gateway", token="tok")
        await gw.connect()
        await gw.connect()  # second call — should be a no-op
        assert mock_open.call_count == 1

    await gw.close()


# ------------------------------------------------------------------ #
# Tests: non-JSON messages are skipped gracefully
# ------------------------------------------------------------------ #


@pytest.mark.asyncio
async def test_non_json_message_is_skipped() -> None:
    """Non-JSON messages from the server must not crash the reader."""
    ws = QueueWebSocket()
    ws.put_nowait(_challenge())
    ws.put_nowait("this is not json!!")

    with _patch_open(ws):
        gw = ProtocolGateway(ws_url="ws://localhost:18789/gateway", token="tok")
        await gw.connect()
        await asyncio.sleep(0.02)  # let the reader process the bad message
        await gw.close()

    assert not gw._connected  # no crash; just disconnected cleanly
