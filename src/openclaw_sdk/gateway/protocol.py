from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import platform
import random
import time
from pathlib import Path
from typing import Any, AsyncIterator

import websockets.exceptions
from websockets.asyncio.client import ClientConnection, connect as ws_connect

from openclaw_sdk.core.constants import EventType as _EventType
from openclaw_sdk.core.exceptions import GatewayError
from openclaw_sdk.core.exceptions import TimeoutError as OCTimeoutError
from openclaw_sdk.core.types import HealthStatus, StreamEvent
from openclaw_sdk.gateway.base import Gateway
from openclaw_sdk.resilience.retry import RetryPolicy

logger = logging.getLogger(__name__)

# Reconnect configuration
_BACKOFF_INITIAL = 1.0  # seconds
_BACKOFF_MAX = 30.0     # seconds
_BACKOFF_JITTER = 0.5   # ± jitter fraction

# SDK version for connect handshake
_SDK_VERSION = "1.0.0"


def _base64url_encode(data: bytes) -> str:
    """RFC 4648 base64url encoding without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


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


def _load_device_identity() -> dict[str, Any] | None:
    """Load device identity from ~/.openclaw/identity/device.json."""
    path = Path.home() / ".openclaw" / "identity" / "device.json"
    if not path.exists():
        logger.debug("No device identity at %s", path)
        return None
    try:
        with path.open() as fh:
            data: dict[str, Any] = json.load(fh)
            return data
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to read device.json: %s", exc)
        return None


def _load_device_auth() -> dict[str, Any] | None:
    """Load device auth tokens from ~/.openclaw/identity/device-auth.json."""
    path = Path.home() / ".openclaw" / "identity" / "device-auth.json"
    if not path.exists():
        logger.debug("No device auth at %s", path)
        return None
    try:
        with path.open() as fh:
            data: dict[str, Any] = json.load(fh)
            return data
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to read device-auth.json: %s", exc)
        return None


def _sign_device_payload(private_key_pem: str, payload: str) -> str:
    """Sign a UTF-8 payload with Ed25519 and return base64url signature.

    Uses the ``cryptography`` library if available, falls back to
    ``PyNaCl`` (``nacl``), or raises if neither is installed.
    """
    payload_bytes = payload.encode("utf-8")

    # Try cryptography first (most common)
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import load_pem_private_key

        key = load_pem_private_key(private_key_pem.encode(), password=None)
        assert isinstance(key, Ed25519PrivateKey)
        sig = key.sign(payload_bytes)
        return _base64url_encode(sig)
    except ImportError:
        pass

    raise GatewayError(
        "Ed25519 signing requires 'cryptography'. "
        "Install with: pip install cryptography"
    )


def _extract_raw_public_key(public_key_pem: str) -> str:
    """Extract the raw 32-byte Ed25519 public key from PEM and return base64url."""
    try:
        from cryptography.hazmat.primitives.serialization import (
            Encoding,
            PublicFormat,
            load_pem_public_key,
        )

        pub = load_pem_public_key(public_key_pem.encode())
        raw = pub.public_bytes(Encoding.Raw, PublicFormat.Raw)
        return _base64url_encode(raw)
    except ImportError:
        # Fallback: parse SPKI DER manually — last 32 bytes of the DER
        pem_body = public_key_pem.replace("-----BEGIN PUBLIC KEY-----", "")
        pem_body = pem_body.replace("-----END PUBLIC KEY-----", "")
        der = base64.b64decode(pem_body.strip())
        # Ed25519 SPKI is exactly 44 bytes: 12-byte header + 32-byte key
        raw = der[-32:]
        return _base64url_encode(raw)


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
        default_timeout: float = 30.0,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self._ws_url = ws_url
        self._token: str | None = token  # may be None; resolved lazily in _do_connect
        self._connect_timeout = connect_timeout
        self._default_timeout = default_timeout
        self._retry_policy = retry_policy

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
        # Track the connect request id so we can set _handshake_done on response
        self._connect_req_id: str | None = None

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _next_id(self) -> str:
        self._req_counter += 1
        return f"req_{self._req_counter}"

    async def _do_connect(self) -> None:
        """Open the WebSocket, start the reader, complete the connect handshake."""
        if self._token is None:
            self._token = _load_token()

        self._handshake_done.clear()
        self._connect_req_id = None

        self._ws = await _open_connection(self._ws_url, self._connect_timeout)

        # Start background reader *before* waiting for the challenge so the
        # challenge message is consumed as soon as it arrives.
        self._reader_task = asyncio.create_task(
            self._reader_loop(), name="openclaw-ws-reader"
        )

        # Wait for the connect handshake to complete.
        # Flow: reader receives connect.challenge → _handle_challenge sends
        # connect RPC → reader receives response → _route_message sets
        # _handshake_done.
        try:
            await asyncio.wait_for(
                self._handshake_done.wait(), timeout=self._connect_timeout
            )
        except asyncio.TimeoutError as exc:
            await self._cleanup_ws()
            raise GatewayError(
                "Timed out waiting for connect handshake with gateway"
            ) from exc

        self._connected = True

    async def _send_json(self, payload: dict[str, Any]) -> None:
        if self._ws is None:
            raise GatewayError("Not connected to gateway")
        await self._ws.send(json.dumps(payload))

    async def _handle_challenge(self, payload: dict[str, Any]) -> None:
        """Respond to connect.challenge with a ``connect`` RPC.

        The gateway expects a full ``connect`` method call with device identity
        and Ed25519 cryptographic signature, not a simple auth token message.

        Signing payload format (v2, with nonce)::

            v2|deviceId|clientId|clientMode|role|scopes|signedAtMs|token|nonce

        This method sends the connect request and returns immediately.
        The handshake completes when ``_route_message`` processes the
        connect response and sets ``_handshake_done``.
        """
        nonce = payload.get("nonce", "")
        logger.debug("Received connect.challenge nonce=%s", nonce)

        # Load device identity and auth
        device = _load_device_identity()
        device_auth = _load_device_auth()

        if not device or not device_auth:
            logger.warning(
                "No device identity/auth found; skipping connect handshake. "
                "Run 'openclaw login' to set up device identity."
            )
            self._handshake_done.set()
            return

        device_id: str = device["deviceId"]
        private_key_pem: str = device["privateKeyPem"]
        public_key_pem: str = device["publicKeyPem"]

        # Get operator token and scopes
        op_token_data = device_auth.get("tokens", {}).get("operator", {})
        auth_token: str = op_token_data.get("token", "")
        role: str = op_token_data.get("role", "operator")
        scopes: list[str] = op_token_data.get("scopes", [])

        # Build the signing payload
        signed_at_ms = int(time.time() * 1000)
        scopes_str = ",".join(scopes)
        sign_payload = "|".join([
            "v2",
            device_id,
            "cli",          # client.id (constant)
            "cli",          # client.mode (constant)
            role,
            scopes_str,
            str(signed_at_ms),
            auth_token,
            nonce,
        ])

        # Sign with Ed25519
        signature = _sign_device_payload(private_key_pem, sign_payload)
        public_key_b64url = _extract_raw_public_key(public_key_pem)

        # Build the connect request
        plat = platform.system().lower()
        connect_params: dict[str, Any] = {
            "minProtocol": 3,
            "maxProtocol": 3,
            "client": {
                "id": "cli",
                "version": _SDK_VERSION,
                "platform": plat,
                "mode": "cli",
            },
            "role": role,
            "scopes": scopes,
            "caps": [],
            "commands": [],
            "permissions": {},
            "auth": {"token": auth_token},
            "locale": "en-US",
            "userAgent": f"openclaw-sdk/{_SDK_VERSION}",
            "device": {
                "id": device_id,
                "publicKey": public_key_b64url,
                "signature": signature,
                "signedAt": signed_at_ms,
                "nonce": nonce,
            },
        }

        # Send as a normal RPC request — the response will be handled by
        # _route_message which checks _connect_req_id to set _handshake_done.
        req_id = self._next_id()
        self._connect_req_id = req_id

        loop = asyncio.get_event_loop()
        future: asyncio.Future[dict[str, Any]] = loop.create_future()
        self._pending[req_id] = future

        await self._send_json({
            "type": "req",
            "id": req_id,
            "method": "connect",
            "params": connect_params,
        })
        # Do NOT await future here — that would deadlock the reader loop.
        # _route_message will resolve the future AND set _handshake_done.

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
        # Gateway uses type="res" with ok/payload/error fields
        msg_id = msg.get("id")
        if msg_id and isinstance(msg_id, str) and msg_id in self._pending:
            future = self._pending.pop(msg_id)
            is_connect = msg_id == self._connect_req_id

            if "error" in msg:
                err = msg["error"]
                exc = GatewayError(
                    err.get("message", "Unknown gateway error"),
                    code=str(err.get("code", "")),
                )
                if not future.done():
                    future.set_exception(exc)
                if is_connect:
                    logger.error("Gateway connect failed: %s", exc)
                    self._handshake_done.set()
            elif "result" in msg or "payload" in msg:
                if not future.done():
                    # Gateway may use "result" or "payload" for the response body
                    raw_result = msg.get("result") or msg.get("payload") or {}
                    # Normalize: if payload is a list, wrap it for dict return type
                    result: dict[str, Any] = (
                        raw_result if isinstance(raw_result, dict) else {"data": raw_result}
                    )
                    future.set_result(result)
                if is_connect:
                    logger.info("Gateway connect handshake completed")
                    self._handshake_done.set()
            elif msg.get("ok") is True:
                # Some responses have ok=true with no payload
                if not future.done():
                    future.set_result({})
                if is_connect:
                    logger.info("Gateway connect handshake completed")
                    self._handshake_done.set()
            else:
                if not future.done():
                    future.set_exception(
                        GatewayError(f"Malformed response (no result/error): {msg}")
                    )
                if is_connect:
                    self._handshake_done.set()
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
            # system-presence may return a list or dict; normalize to dict.
            details: dict[str, Any] = (
                result if isinstance(result, dict) else {"nodes": result}
            )
            return HealthStatus(
                healthy=True,
                latency_ms=latency_ms,
                details=details,
            )
        except GatewayError as exc:
            return HealthStatus(healthy=False, details={"error": str(exc)})

    async def _call_once(
        self,
        method: str,
        params: dict[str, Any] | None,
        idempotency_key: str | None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """Send a single RPC request and await the response (no retry)."""
        if not self._connected:
            raise GatewayError("Not connected to gateway. Call await gw.connect() first.")

        effective_timeout = timeout if timeout is not None else self._default_timeout

        req_id = self._next_id()
        envelope: dict[str, Any] = {
            "type": "req",
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
            return await asyncio.wait_for(future, timeout=effective_timeout)
        except asyncio.TimeoutError as exc:
            self._pending.pop(req_id, None)
            raise OCTimeoutError(
                f"Gateway call '{method}' timed out after {effective_timeout}s"
            ) from exc
        except GatewayError:
            raise
        except Exception as exc:
            raise GatewayError(f"Unexpected error awaiting response: {exc}") from exc

    async def call(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        timeout: float | None = None,
        idempotency_key: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Send an RPC request and await the response.

        When a :class:`~openclaw_sdk.resilience.retry.RetryPolicy` is
        configured, transient failures are retried automatically with
        exponential backoff.

        Args:
            method: Gateway method name, e.g. ``"sessions.list"``.
            params: Method parameters.  Defaults to ``{}``.
            timeout: Per-call timeout in seconds.  If ``None``, uses the
                instance ``default_timeout`` (default 30 s).
            idempotency_key: Optional idempotency key passed through to the
                gateway as ``idempotencyKey`` in the params dict.

        Returns:
            The ``result`` dict from the gateway response.

        Raises:
            GatewayError: On protocol error or gateway-reported error.
            TimeoutError: If the gateway does not respond within *timeout*.
        """
        if self._retry_policy is not None:
            return await self._retry_policy.execute(
                self._call_once, method, params, idempotency_key, timeout
            )
        return await self._call_once(method, params, idempotency_key, timeout)

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
