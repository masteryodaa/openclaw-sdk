from __future__ import annotations

import time
from typing import Any, AsyncIterator

import httpx

from openclaw_sdk.core.exceptions import GatewayError
from openclaw_sdk.core.types import HealthStatus, StreamEvent
from openclaw_sdk.gateway.base import Gateway

# Method → (HTTP verb, URL path) routing table.
# Only the methods verified against protocol-notes.md are mapped here.
_METHOD_ROUTES: dict[str, tuple[str, str]] = {
    # chat
    "chat.send": ("POST", "/v1/responses"),
    "chat.history": ("GET", "/v1/chat/history"),
    "chat.abort": ("POST", "/v1/chat/abort"),
    "chat.inject": ("POST", "/v1/chat/inject"),
    # sessions
    "sessions.list": ("GET", "/v1/sessions"),
    "sessions.preview": ("POST", "/v1/sessions/preview"),
    "sessions.reset": ("POST", "/v1/sessions/reset"),
    "sessions.delete": ("DELETE", "/v1/sessions"),
    "sessions.compact": ("POST", "/v1/sessions/compact"),
    "sessions.patch": ("PATCH", "/v1/sessions"),
    # config
    "config.get": ("GET", "/v1/config"),
    "config.schema": ("GET", "/v1/config/schema"),
    "config.set": ("PUT", "/v1/config"),
    "config.patch": ("PATCH", "/v1/config"),
    # cron
    "cron.list": ("GET", "/v1/cron"),
    "cron.status": ("GET", "/v1/cron/status"),
    "cron.add": ("POST", "/v1/cron"),
    "cron.update": ("PATCH", "/v1/cron"),
    "cron.remove": ("DELETE", "/v1/cron"),
    "cron.run": ("POST", "/v1/cron/run"),
    "cron.runs": ("GET", "/v1/cron/runs"),
    # channels
    "channels.status": ("GET", "/v1/channels/status"),
    "channels.logout": ("POST", "/v1/channels/logout"),
    "web.login.start": ("POST", "/v1/channels/login/start"),
    "web.login.wait": ("POST", "/v1/channels/login/wait"),
    # node
    "node.list": ("GET", "/v1/nodes"),
    # logs
    "logs.tail": ("GET", "/v1/logs/tail"),
    # system
    "system-presence": ("GET", "/v1/system/presence"),
}


class OpenAICompatGateway(Gateway):
    """HTTP-only gateway adapter for OpenAI-compatible endpoints.

    Translates the SDK's method-based RPC calls to HTTP requests against an
    OpenAI-compatible REST API (e.g. a local OpenClaw HTTP bridge or a
    hosted service that speaks the same protocol).

    Note: This gateway does NOT support push-event streaming.  Calling
    :meth:`subscribe` raises :class:`NotImplementedError`.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        *,
        timeout: float = 30.0,
    ) -> None:
        """Create an OpenAICompatGateway.

        Args:
            base_url: Base URL of the OpenAI-compatible HTTP API,
                e.g. ``"http://localhost:8080"``.
            api_key: Optional Bearer token sent as
                ``Authorization: Bearer <api_key>``.
            timeout: HTTP request timeout in seconds.
        """
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------ #
    # Connection lifecycle
    # ------------------------------------------------------------------ #

    async def connect(self) -> None:
        """Create the underlying :class:`httpx.AsyncClient`."""
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers=headers,
            timeout=self._timeout,
        )

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    # ------------------------------------------------------------------ #
    # Health check
    # ------------------------------------------------------------------ #

    async def health(self) -> HealthStatus:
        """Check service health via ``GET /health`` (or ``/v1/health``)."""
        if self._client is None:
            return HealthStatus(healthy=False, details={"error": "not connected"})

        t0 = time.monotonic()
        for path in ("/health", "/v1/health"):
            try:
                resp = await self._client.get(path)
                latency_ms = (time.monotonic() - t0) * 1000.0
                if resp.status_code < 400:
                    try:
                        details: dict[str, Any] = resp.json()
                    except Exception:  # noqa: BLE001
                        details = {"status": resp.text}
                    return HealthStatus(
                        healthy=True,
                        latency_ms=latency_ms,
                        details=details,
                    )
            except httpx.RequestError:
                pass

        latency_ms = (time.monotonic() - t0) * 1000.0
        return HealthStatus(
            healthy=False,
            latency_ms=latency_ms,
            details={"error": "health endpoint unreachable"},
        )

    # ------------------------------------------------------------------ #
    # RPC call → HTTP translation
    # ------------------------------------------------------------------ #

    async def call(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Translate an RPC-style method call to an HTTP request.

        Args:
            method: RPC method name, e.g. ``"chat.send"`` or
                ``"sessions.list"``.
            params: Request parameters / body.
            timeout: Per-call timeout (unused; HTTP timeout is set at
                client level).

        Returns:
            Parsed JSON response body as a dict.

        Raises:
            GatewayError: On HTTP error or unknown method.
        """
        if self._client is None:
            raise GatewayError(
                "OpenAICompatGateway not connected. Call await gw.connect() first."
            )

        if method not in _METHOD_ROUTES:
            raise GatewayError(
                f"OpenAICompatGateway: unknown method '{method}'. "
                "Only HTTP-mapped methods are supported."
            )

        verb, path = _METHOD_ROUTES[method]
        body = params or {}

        try:
            if verb == "GET":
                resp = await self._client.get(path, params=body if body else None)
            elif verb == "POST":
                resp = await self._client.post(path, json=body)
            elif verb == "PUT":
                resp = await self._client.put(path, json=body)
            elif verb == "PATCH":
                resp = await self._client.patch(path, json=body)
            elif verb == "DELETE":
                resp = await self._client.delete(path, params=body if body else None)
            else:
                raise GatewayError(f"Unsupported HTTP verb: {verb}")
        except httpx.RequestError as exc:
            raise GatewayError(f"HTTP request failed for {method}: {exc}") from exc

        if resp.status_code >= 400:
            try:
                err_body: dict[str, Any] = resp.json()
            except Exception:  # noqa: BLE001
                err_body = {"raw": resp.text}
            raise GatewayError(
                f"Gateway returned HTTP {resp.status_code} for {method}",
                code=str(resp.status_code),
                details=err_body,
            )

        try:
            result: dict[str, Any] = resp.json()
        except Exception as exc:  # noqa: BLE001
            raise GatewayError(
                f"Non-JSON response from gateway for {method}: {resp.text[:200]}"
            ) from exc

        return result

    # ------------------------------------------------------------------ #
    # Streaming (not supported)
    # ------------------------------------------------------------------ #

    async def subscribe(
        self, event_types: list[str] | None = None
    ) -> AsyncIterator[StreamEvent]:
        """Not supported — OpenAICompatGateway is HTTP-only.

        Raises:
            NotImplementedError: Always.
        """
        raise NotImplementedError(
            "OpenAICompatGateway is HTTP-only and does not support streaming events. "
            "Use ProtocolGateway for WebSocket-based event subscriptions."
        )
