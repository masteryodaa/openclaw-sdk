from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import time
from pathlib import Path
from typing import Any, AsyncIterator

import websockets.exceptions
from websockets.asyncio.client import ClientConnection, connect as ws_connect

from openclaw_sdk.core.constants import EventType as _EventType
from openclaw_sdk.core.exceptions import GatewayError
from openclaw_sdk.core.types import HealthStatus, StreamEvent
from openclaw_sdk.gateway.base import Gateway

logger = logging.getLogger(__name__)

# Reconnect configuration
_BACKOFF_INITIAL = 1.0  # seconds
_BACKOFF_MAX = 30.0     # seconds
_BACKOFF_JITTER = 0.5   # ± jitter fraction


def _load_token() -> str | None:
    """Load the gateway auth token.

    Priority:
    1. OPENCLAW_GATEWAY_TOKEN environment variable
    2. ~/.openclaw/openclaw.json at gateway.auth.token
    3. None (warn; some methods may work unauthenticated)
    """
    env_token = os.environ.get("OPENCLAW_GATEWAY_TOKEN")
    if env_token:
        return env_token

    config_path = Path.home() / ".openclaw" / "openclaw.json"
    if config_path.exists():
        try:
            with config_path.open() as fh:
                data = json.load(fh)
            token: str | None = (
                data.get("gateway", {}).get("auth", {}).get("token")
            )
            if token:
                return token
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to read openclaw.json: %s", exc)

    logger.warning(
        "No gateway auth token found. "
        "Set OPENCLAW_GATEWAY_TOKEN or configure ~/.openclaw/openclaw.json. "
        "Some methods may fail."
    )
    return None


async def _open_connection(ws_url: str, timeout: float) -> ClientConnection:
    """Open a WebSocket connection.  Isolated for easy mocking in tests."""
    try:
        return await asyncio.wait_for(ws_connect(ws_url), timeout=timeout)
    except asyncio.TimeoutError as exc:
        raise GatewayError(
            f"Timed out connecting to {ws_url} after {timeout}s"
        ) from exc


class ProtocolGateway(Gateway):
    """WebSocket RPC gateway client for the OpenClaw gateway protocol.

    Connection & auth flow (from protocol-notes.md):
    - Connects to ws://127.0.0.1:18789/gateway (configurable)
    - Gateway immediately pushes a connect.challenge event with a nonce + ts
    - SDK responds with the auth token (read from env/config)
    - Subsequent calls use JSON-RPC-style envelopes:
        Request:  {"id": "req_N", "method": "...", "params": {...}}
        Response: {"id": "req_N", "result": {...}}
        Error:    {"id": "req_N", "error": {"code": ..., "message": "..."}}
        Push:     {"type": "event", "event": "...", "payload": {...}}

    Reconnect strategy: exponential backoff starting at 1 s, capped at 30 s,
    with ±50% jitter.  In-flight requests are failed immediately on disconnect
    so the caller can retry.
    """

    def __init__(
        self,
        ws_url: str = "ws://127.0.0.1:18789/gateway",
        token: str | None = None,
        *,
        connect_timeout: float = 10.0,
    ) -> None:
        self._ws_url = ws_url
        self._token: str | None = token  # may be None; resolved lazily in _do_connect
        self._connect_timeout = connect_timeout

        self._ws: ClientConnection | None = None
        self._reader_task: asyncio.Task[None] | None = None

        # Request correlation: id → Future awaiting the response
        self._pending: dict[str, asyncio.Future[dict[str, Any]]] = {}
        self._req_counter = 0

        # Push-event subscribers: list of (filter, queue) pairs
        self._subscribers: list[
            tuple[list[str] | None, asyncio.Queue[StreamEvent | None]]
        ] = []

        self._closed = False
        self._connected = False

        # Set after the connect.challenge handshake completes
        self._handshake_done: asyncio.Event = asyncio.Event()

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _next_id(self) -> str:
        self._req_counter += 1
        return f"req_{self._req_counter}"

    async def _do_connect(self) -> None:
        """Open the WebSocket, start the reader, wait for connect.challenge."""
        if self._token is None:
            self._token = _load_token()

        self._handshake_done.clear()

        self._ws = await _open_connection(self._ws_url, self._connect_timeout)

        # Start background reader *before* waiting for the challenge so the
        # challenge message is consumed as soon as it arrives.
        self._reader_task = asyncio.create_task(
            self._reader_loop(), name="openclaw-ws-reader"
        )

        # Wait for the handshake to complete (challenge received + auth sent).
        try:
            await asyncio.wait_for(
                self._handshake_done.wait(), timeout=self._connect_timeout
            )
        except asyncio.TimeoutError as exc:
            await self._cleanup_ws()
            raise GatewayError(
                "Timed out waiting for connect.challenge from gateway"
            ) from exc

        self._connected = True

    async def _send_json(self, payload: dict[str, Any]) -> None:
        if self._ws is None:
            raise GatewayError("Not connected to gateway")
        await self._ws.send(json.dumps(payload))

    async def _handle_challenge(self, payload: dict[str, Any]) -> None:
        """Respond to connect.challenge with the auth token."""
        nonce = payload.get("nonce", "")
        logger.debug("Received connect.challenge nonce=%s", nonce)
        if self._token:
            await self._send_json(
                {
                    "type": "auth",
                    "token": self._token,
                    "nonce": nonce,
                }
            )
        else:
            logger.warning(
                "No auth token available; skipping auth response to challenge"
            )
        self._handshake_done.set()

    def _dispatch_event(self, event_name: str, payload: dict[str, Any]) -> None:
        """Route a push event to all matching subscriber queues."""
        # Map the raw gateway event name to a known EventType where possible.
        # Unknown event types are surfaced under the ERROR sentinel so callers
        # can inspect event_name via data["event"].
        try:
            ev_type = _EventType(event_name)
        except ValueError:
            ev_type = _EventType.ERROR

        stream_event = StreamEvent(
            event_type=ev_type,
            data={"event": event_name, "payload": payload},
        )

        for filter_types, queue in self._subscribers:
            if filter_types is None or event_name in filter_types:
                queue.put_nowait(stream_event)

    async def _reader_loop(self) -> None:
        """Background task: consume incoming WebSocket messages."""
        assert self._ws is not None

        try:
            async for raw in self._ws:
                if isinstance(raw, bytes):
                    raw = raw.decode()
                try:
                    msg: dict[str, Any] = json.loads(raw)
                except json.JSONDecodeError:
                    logger.warning("Received non-JSON message: %.200s", raw)
                    continue

                await self._route_message(msg)
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
        except Exception as exc:  # noqa: BLE001
            logger.error("Reader loop error: %s", exc)
        finally:
            self._connected = False
            self._fail_pending(GatewayError("WebSocket disconnected"))
            self._signal_subscriber_disconnect()

    async def _route_message(self, msg: dict[str, Any]) -> None:
        """Route a parsed message to the right handler."""
        # Push event (no id field; type == "event")
        if msg.get("type") == "event":
            event_name: str = msg.get("event", "")
            payload: dict[str, Any] = msg.get("payload") or {}

            if event_name == "connect.challenge":
                await self._handle_challenge(payload)
            else:
                self._dispatch_event(event_name, payload)
            return

        # RPC response (has id field)
        msg_id = msg.get("id")
        if msg_id and isinstance(msg_id, str) and msg_id in self._pending:
            future = self._pending.pop(msg_id)
            if "error" in msg:
                err = msg["error"]
                exc = GatewayError(
                    err.get("message", "Unknown gateway error"),
                    code=str(err.get("code", "")),
                )
                if not future.done():
                    future.set_exception(exc)
            elif "result" in msg:
                if not future.done():
                    result: dict[str, Any] = msg["result"] or {}
                    future.set_result(result)
            else:
                if not future.done():
                    future.set_exception(
                        GatewayError(f"Malformed response (no result/error): {msg}")
                    )
            return

        logger.debug("Unrouted message: %s", msg)

    def _fail_pending(self, exc: Exception) -> None:
        """Fail all in-flight requests with the given exception."""
        pending = list(self._pending.values())
        self._pending.clear()
        for future in pending:
            if not future.done():
                future.set_exception(exc)

    def _signal_subscriber_disconnect(self) -> None:
        """Send None sentinel to all subscriber queues to end their iterators."""
        for _, queue in self._subscribers:
            queue.put_nowait(None)

    async def _cleanup_ws(self) -> None:
        """Cancel the reader task and close the WebSocket."""
        if self._reader_task is not None and not self._reader_task.done():
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
        self._reader_task = None

        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:  # noqa: BLE001
                pass
            self._ws = None

    # ------------------------------------------------------------------ #
    # Reconnect loop
    # ------------------------------------------------------------------ #

    async def _connect_with_backoff(self) -> None:
        """Try to connect, retrying with exponential backoff on failure."""
        delay = _BACKOFF_INITIAL
        attempt = 0
        while not self._closed:
            attempt += 1
            try:
                await self._do_connect()
                logger.info("Connected to OpenClaw gateway at %s", self._ws_url)
                return
            except GatewayError:
                # Fatal gateway errors (e.g. auth failure) — re-raise
                raise
            except Exception as exc:  # noqa: BLE001
                if self._closed:
                    raise
                jitter = random.uniform(-_BACKOFF_JITTER * delay, _BACKOFF_JITTER * delay)
                wait = min(delay + jitter, _BACKOFF_MAX)
                logger.warning(
                    "Gateway connect attempt %d failed (%s); retrying in %.1fs",
                    attempt,
                    exc,
                    wait,
                )
                await asyncio.sleep(wait)
                delay = min(delay * 2, _BACKOFF_MAX)

    # ------------------------------------------------------------------ #
    # Gateway ABC implementation
    # ------------------------------------------------------------------ #

    async def connect(self) -> None:
        """Connect to the OpenClaw gateway and complete the auth handshake."""
        if self._connected:
            return
        self._closed = False
        await self._connect_with_backoff()

    async def close(self) -> None:
        """Close the gateway connection and stop the reader task."""
        self._closed = True
        self._connected = False
        self._fail_pending(GatewayError("Gateway closed"))
        self._signal_subscriber_disconnect()
        await self._cleanup_ws()

    async def health(self) -> HealthStatus:
        """Return connection health via a lightweight system-presence call."""
        if not self._connected:
            return HealthStatus(healthy=False)
        t0 = time.monotonic()
        try:
            result = await self.call("system-presence", {})
            latency_ms = (time.monotonic() - t0) * 1000.0
            return HealthStatus(
                healthy=True,
                latency_ms=latency_ms,
                details=result,
            )
        except GatewayError as exc:
            return HealthStatus(healthy=False, details={"error": str(exc)})

    async def call(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        idempotency_key: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Send an RPC request and await the response.

        Args:
            method: Gateway method name, e.g. ``"sessions.list"``.
            params: Method parameters.  Defaults to ``{}``.
            idempotency_key: Optional idempotency key passed through to the
                gateway as ``idempotencyKey`` in the params dict.

        Returns:
            The ``result`` dict from the gateway response.

        Raises:
            GatewayError: On protocol error or gateway-reported error.
        """
        if not self._connected:
            raise GatewayError("Not connected to gateway. Call await gw.connect() first.")

        req_id = self._next_id()
        envelope: dict[str, Any] = {
            "id": req_id,
            "method": method,
            "params": dict(params) if params is not None else {},
        }
        if idempotency_key is not None:
            # Verified field name from protocol-notes.md
            envelope["params"]["idempotencyKey"] = idempotency_key

        loop = asyncio.get_event_loop()
        future: asyncio.Future[dict[str, Any]] = loop.create_future()
        self._pending[req_id] = future

        try:
            await self._send_json(envelope)
        except Exception as exc:
            self._pending.pop(req_id, None)
            raise GatewayError(f"Failed to send request: {exc}") from exc

        try:
            return await future
        except GatewayError:
            raise
        except Exception as exc:
            raise GatewayError(f"Unexpected error awaiting response: {exc}") from exc

    async def subscribe(
        self, event_types: list[str] | None = None
    ) -> AsyncIterator[StreamEvent]:
        """Subscribe to push events from the gateway.

        Args:
            event_types: Optional whitelist of raw event names (e.g.
                ``["task.done", "task.progress"]``).  ``None`` means all events.

        Returns:
            An async iterator yielding :class:`StreamEvent` objects.
        """
        if not self._connected:
            raise GatewayError("Not connected. Call await gw.connect() first.")
        queue: asyncio.Queue[StreamEvent | None] = asyncio.Queue()
        self._subscribers.append((event_types, queue))
        return self._stream_events(queue)

    async def _stream_events(
        self,
        queue: asyncio.Queue[StreamEvent | None],
    ) -> AsyncIterator[StreamEvent]:
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield event
        finally:
            # Unregister this subscriber when the iterator is garbage-collected
            self._subscribers[:] = [
                (f, q) for f, q in self._subscribers if q is not queue
            ]
