"""Tests for gateway/openai_compat.py — OpenAICompatGateway."""
from __future__ import annotations

from typing import Any

import httpx
import pytest

from openclaw_sdk.core.exceptions import GatewayError
from openclaw_sdk.core.types import HealthStatus
from openclaw_sdk.gateway.openai_compat import OpenAICompatGateway, _METHOD_ROUTES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_gateway(
    base_url: str = "http://localhost:8080",
    api_key: str | None = None,
    timeout: float = 30.0,
) -> OpenAICompatGateway:
    return OpenAICompatGateway(base_url=base_url, api_key=api_key, timeout=timeout)


def _mock_transport(responses: dict[str, Any]) -> httpx.MockTransport:
    """Build an httpx.MockTransport that returns preset responses keyed by path."""

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path in responses:
            resp_spec = responses[path]
            if isinstance(resp_spec, httpx.Response):
                return resp_spec
            # Assume it's a dict to be returned as JSON
            return httpx.Response(200, json=resp_spec)
        return httpx.Response(404, json={"error": "not found"})

    return httpx.MockTransport(handler)


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


def test_base_url_strips_trailing_slash() -> None:
    gw = _make_gateway(base_url="http://localhost:8080/")
    assert gw._base_url == "http://localhost:8080"


def test_api_key_stored() -> None:
    gw = _make_gateway(api_key="sk-test")
    assert gw._api_key == "sk-test"


def test_client_starts_none() -> None:
    gw = _make_gateway()
    assert gw._client is None


# ---------------------------------------------------------------------------
# health() — before connect()
# ---------------------------------------------------------------------------


async def test_health_not_connected_returns_unhealthy() -> None:
    gw = _make_gateway()
    status = await gw.health()
    assert isinstance(status, HealthStatus)
    assert status.healthy is False
    assert "not connected" in status.details.get("error", "")


# ---------------------------------------------------------------------------
# call() — before connect() raises GatewayError
# ---------------------------------------------------------------------------


async def test_call_not_connected_raises_gateway_error() -> None:
    gw = _make_gateway()
    with pytest.raises(GatewayError, match="not connected"):
        await gw.call("sessions.list", {})


# ---------------------------------------------------------------------------
# call() — unknown method raises GatewayError
# ---------------------------------------------------------------------------


async def test_call_unknown_method_raises_gateway_error() -> None:
    gw = _make_gateway()
    await gw.connect()
    try:
        with pytest.raises(GatewayError, match="unknown method"):
            await gw.call("nonexistent.method", {})
    finally:
        await gw.close()


# ---------------------------------------------------------------------------
# subscribe() — always raises NotImplementedError
# ---------------------------------------------------------------------------


async def test_subscribe_raises_not_implemented() -> None:
    gw = _make_gateway()
    with pytest.raises(NotImplementedError):
        await gw.subscribe()


async def test_subscribe_raises_not_implemented_after_connect() -> None:
    gw = _make_gateway()
    await gw.connect()
    try:
        with pytest.raises(NotImplementedError):
            await gw.subscribe(event_types=["content"])
    finally:
        await gw.close()


# ---------------------------------------------------------------------------
# connect() and close()
# ---------------------------------------------------------------------------


async def test_connect_creates_client() -> None:
    gw = _make_gateway()
    await gw.connect()
    try:
        assert gw._client is not None
        assert isinstance(gw._client, httpx.AsyncClient)
    finally:
        await gw.close()


async def test_connect_with_api_key_sets_authorization_header() -> None:
    gw = _make_gateway(api_key="sk-mytoken")
    await gw.connect()
    try:
        assert gw._client is not None
        # The Authorization header is set in the default headers of the client
        auth_header = gw._client.headers.get("Authorization")
        assert auth_header == "Bearer sk-mytoken"
    finally:
        await gw.close()


async def test_close_sets_client_to_none() -> None:
    gw = _make_gateway()
    await gw.connect()
    assert gw._client is not None
    await gw.close()
    assert gw._client is None


async def test_close_when_not_connected_is_noop() -> None:
    gw = _make_gateway()
    # Should not raise
    await gw.close()
    assert gw._client is None


# ---------------------------------------------------------------------------
# call() — GET method via mock transport
# ---------------------------------------------------------------------------


async def test_call_get_sessions_list() -> None:
    gw = _make_gateway()
    await gw.connect()
    # Replace inner client with mock transport
    gw._client = httpx.AsyncClient(
        base_url="http://localhost:8080",
        transport=_mock_transport({"/v1/sessions": {"sessions": []}}),
    )
    try:
        result = await gw.call("sessions.list", {})
        assert result == {"sessions": []}
    finally:
        await gw.close()


# ---------------------------------------------------------------------------
# call() — POST method via mock transport
# ---------------------------------------------------------------------------


async def test_call_post_chat_send() -> None:
    gw = _make_gateway()
    await gw.connect()
    gw._client = httpx.AsyncClient(
        base_url="http://localhost:8080",
        transport=_mock_transport({"/v1/responses": {"runId": "r1", "status": "started"}}),
    )
    try:
        result = await gw.call("chat.send", {"sessionKey": "agent:bot:main", "message": "hi"})
        assert result["runId"] == "r1"
    finally:
        await gw.close()


# ---------------------------------------------------------------------------
# call() — HTTP 4xx/5xx raises GatewayError with code
# ---------------------------------------------------------------------------


async def test_call_http_400_raises_gateway_error() -> None:
    gw = _make_gateway()
    await gw.connect()
    gw._client = httpx.AsyncClient(
        base_url="http://localhost:8080",
        transport=_mock_transport(
            {"/v1/sessions": httpx.Response(400, json={"error": "bad request"})}
        ),
    )
    try:
        with pytest.raises(GatewayError) as exc_info:
            await gw.call("sessions.list", {})
        assert exc_info.value.code == "400"
        assert "400" in str(exc_info.value)
    finally:
        await gw.close()


async def test_call_http_500_raises_gateway_error() -> None:
    gw = _make_gateway()
    await gw.connect()
    gw._client = httpx.AsyncClient(
        base_url="http://localhost:8080",
        transport=_mock_transport(
            {"/v1/sessions": httpx.Response(500, text="Internal Server Error")}
        ),
    )
    try:
        with pytest.raises(GatewayError) as exc_info:
            await gw.call("sessions.list", {})
        assert exc_info.value.code == "500"
    finally:
        await gw.close()


# ---------------------------------------------------------------------------
# call() — network error raises GatewayError
# ---------------------------------------------------------------------------


async def test_call_request_error_raises_gateway_error() -> None:
    def failing_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    gw = _make_gateway()
    await gw.connect()
    gw._client = httpx.AsyncClient(
        base_url="http://localhost:8080",
        transport=httpx.MockTransport(failing_handler),
    )
    try:
        with pytest.raises(GatewayError, match="HTTP request failed"):
            await gw.call("sessions.list", {})
    finally:
        await gw.close()


# ---------------------------------------------------------------------------
# call() — non-JSON response raises GatewayError
# ---------------------------------------------------------------------------


async def test_call_non_json_response_raises_gateway_error() -> None:
    gw = _make_gateway()
    await gw.connect()
    gw._client = httpx.AsyncClient(
        base_url="http://localhost:8080",
        transport=_mock_transport(
            {"/v1/sessions": httpx.Response(200, text="plain text response")}
        ),
    )
    try:
        with pytest.raises(GatewayError, match="Non-JSON response"):
            await gw.call("sessions.list", {})
    finally:
        await gw.close()


# ---------------------------------------------------------------------------
# call() — PATCH, PUT, DELETE methods
# ---------------------------------------------------------------------------


async def test_call_put_config_set() -> None:
    gw = _make_gateway()
    await gw.connect()
    gw._client = httpx.AsyncClient(
        base_url="http://localhost:8080",
        transport=_mock_transport({"/v1/config": {"ok": True}}),
    )
    try:
        result = await gw.call("config.set", {"setting": "value"})
        assert result == {"ok": True}
    finally:
        await gw.close()


async def test_call_patch_sessions() -> None:
    gw = _make_gateway()
    await gw.connect()
    gw._client = httpx.AsyncClient(
        base_url="http://localhost:8080",
        transport=_mock_transport({"/v1/sessions": {"updated": True}}),
    )
    try:
        result = await gw.call("sessions.patch", {"key": "agent:bot:main"})
        assert result == {"updated": True}
    finally:
        await gw.close()


async def test_call_delete_sessions() -> None:
    gw = _make_gateway()
    await gw.connect()
    gw._client = httpx.AsyncClient(
        base_url="http://localhost:8080",
        transport=_mock_transport({"/v1/sessions": {"deleted": True}}),
    )
    try:
        result = await gw.call("sessions.delete", {})
        assert result == {"deleted": True}
    finally:
        await gw.close()


# ---------------------------------------------------------------------------
# health() — successful response via mock transport
# ---------------------------------------------------------------------------


async def test_health_connected_healthy_response() -> None:
    gw = _make_gateway()
    await gw.connect()
    gw._client = httpx.AsyncClient(
        base_url="http://localhost:8080",
        transport=_mock_transport({"/health": {"status": "ok"}}),
    )
    try:
        status = await gw.health()
        assert status.healthy is True
        assert status.latency_ms is not None
    finally:
        await gw.close()


async def test_health_connected_v1_health_fallback() -> None:
    """When /health returns 404, should try /v1/health."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(404, json={"error": "not found"})
        if request.url.path == "/v1/health":
            return httpx.Response(200, json={"status": "ok"})
        return httpx.Response(404)

    gw = _make_gateway()
    await gw.connect()
    gw._client = httpx.AsyncClient(
        base_url="http://localhost:8080",
        transport=httpx.MockTransport(handler),
    )
    try:
        status = await gw.health()
        assert status.healthy is True
    finally:
        await gw.close()


async def test_health_connected_all_fail_returns_unhealthy() -> None:
    """Both /health endpoints failing → healthy=False."""

    def failing_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    gw = _make_gateway()
    await gw.connect()
    gw._client = httpx.AsyncClient(
        base_url="http://localhost:8080",
        transport=httpx.MockTransport(failing_handler),
    )
    try:
        status = await gw.health()
        assert status.healthy is False
        assert "unreachable" in status.details.get("error", "")
    finally:
        await gw.close()


async def test_health_non_json_response_is_handled() -> None:
    """A 200 response with non-JSON body is parsed as text fallback."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="OK")

    gw = _make_gateway()
    await gw.connect()
    gw._client = httpx.AsyncClient(
        base_url="http://localhost:8080",
        transport=httpx.MockTransport(handler),
    )
    try:
        status = await gw.health()
        assert status.healthy is True
        assert status.details.get("status") == "OK"
    finally:
        await gw.close()


# ---------------------------------------------------------------------------
# _METHOD_ROUTES coverage — all known methods are mapped
# ---------------------------------------------------------------------------


def test_method_routes_contains_chat_send() -> None:
    assert "chat.send" in _METHOD_ROUTES
    assert _METHOD_ROUTES["chat.send"] == ("POST", "/v1/responses")


def test_method_routes_contains_sessions_list() -> None:
    assert "sessions.list" in _METHOD_ROUTES
    assert _METHOD_ROUTES["sessions.list"][0] == "GET"


def test_method_routes_contains_channels_status() -> None:
    assert "channels.status" in _METHOD_ROUTES
