"""Tests for webhooks/manager.py — WebhookManager, delivery engine, and models."""
from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from openclaw_sdk.webhooks.manager import (
    DeliveryStatus,
    WebhookConfig,
    WebhookDelivery,
    WebhookDeliveryEngine,
    WebhookManager,
)


def _make_mock_client(**kwargs: Any) -> MagicMock:
    """Create a mock httpx.AsyncClient with an AsyncMock post method."""
    client = MagicMock()
    client.post = AsyncMock(**kwargs)
    return client


def _ok_response() -> httpx.Response:
    return httpx.Response(200, request=httpx.Request("POST", "https://x.com"))


def _fail_response(status: int = 500) -> httpx.Response:
    return httpx.Response(status, request=httpx.Request("POST", "https://x.com"))


# ---------------------------------------------------------------------------
# WebhookConfig model tests
# ---------------------------------------------------------------------------


class TestWebhookConfig:
    def test_defaults(self) -> None:
        cfg = WebhookConfig(name="test", url="https://example.com/hook")
        assert cfg.name == "test"
        assert cfg.url == "https://example.com/hook"
        assert cfg.events == []
        assert cfg.secret is None
        assert cfg.enabled is True
        assert cfg.max_retries == 3
        assert cfg.timeout_seconds == 10.0
        assert cfg.headers == {}

    def test_full_construction(self) -> None:
        cfg = WebhookConfig(
            name="alerts",
            url="https://hooks.example.com/alert",
            events=["agent.started", "agent.completed"],
            secret="super-secret",
            enabled=False,
            max_retries=5,
            timeout_seconds=30.0,
            headers={"Authorization": "Bearer tok"},
        )
        assert cfg.name == "alerts"
        assert cfg.events == ["agent.started", "agent.completed"]
        assert cfg.secret == "super-secret"
        assert cfg.enabled is False
        assert cfg.max_retries == 5
        assert cfg.timeout_seconds == 30.0
        assert cfg.headers == {"Authorization": "Bearer tok"}


# ---------------------------------------------------------------------------
# WebhookDelivery model tests
# ---------------------------------------------------------------------------


class TestWebhookDelivery:
    def test_defaults(self) -> None:
        d = WebhookDelivery(
            webhook_name="hook1",
            event_type="agent.started",
            max_attempts=4,
        )
        assert d.webhook_name == "hook1"
        assert d.event_type == "agent.started"
        assert d.status == DeliveryStatus.PENDING
        assert d.attempts == 0
        assert d.max_attempts == 4
        assert d.response_status is None
        assert d.error is None
        assert d.last_attempt_at is None
        assert d.created_at is not None

    def test_auto_generated_id(self) -> None:
        d1 = WebhookDelivery(
            webhook_name="hook1", event_type="e", max_attempts=1
        )
        d2 = WebhookDelivery(
            webhook_name="hook1", event_type="e", max_attempts=1
        )
        assert d1.delivery_id != d2.delivery_id
        assert len(d1.delivery_id) == 36  # UUID4 format


# ---------------------------------------------------------------------------
# HMAC signature tests
# ---------------------------------------------------------------------------


class TestComputeSignature:
    def test_correct_hex_digest(self) -> None:
        payload = b'{"event":"test"}'
        secret = "my-secret"
        expected = hmac.new(
            secret.encode("utf-8"), payload, hashlib.sha256
        ).hexdigest()
        result = WebhookDeliveryEngine.compute_signature(payload, secret)
        assert result == expected

    def test_different_payloads_differ(self) -> None:
        secret = "key"
        sig1 = WebhookDeliveryEngine.compute_signature(b"payload1", secret)
        sig2 = WebhookDeliveryEngine.compute_signature(b"payload2", secret)
        assert sig1 != sig2


# ---------------------------------------------------------------------------
# Delivery engine tests (httpx mocked)
# ---------------------------------------------------------------------------


class TestDeliveryEngine:
    async def test_successful_post(self) -> None:
        mock_client = _make_mock_client(return_value=_ok_response())

        engine = WebhookDeliveryEngine(http_client=mock_client)
        config = WebhookConfig(name="h1", url="https://example.com/hook")
        delivery = await engine.deliver(config, "agent.done", {"msg": "hi"})

        assert delivery.status == DeliveryStatus.SUCCESS
        assert delivery.response_status == 200
        assert delivery.attempts == 1

        # Verify post was called with correct args
        call_kwargs = mock_client.post.call_args
        assert call_kwargs.kwargs["headers"]["X-Webhook-Event"] == "agent.done"
        assert "X-Webhook-Signature" not in call_kwargs.kwargs["headers"]

    async def test_includes_signature_when_secret_set(self) -> None:
        mock_client = _make_mock_client(return_value=_ok_response())

        engine = WebhookDeliveryEngine(http_client=mock_client)
        config = WebhookConfig(
            name="h1", url="https://example.com/hook", secret="s3cret"
        )
        payload = {"data": "value"}
        delivery = await engine.deliver(config, "event.x", payload)

        assert delivery.status == DeliveryStatus.SUCCESS
        call_kwargs = mock_client.post.call_args
        headers = call_kwargs.kwargs["headers"]
        assert "X-Webhook-Signature" in headers

        # Verify the signature matches expected HMAC
        payload_bytes = json.dumps(payload, default=str).encode("utf-8")
        expected_sig = WebhookDeliveryEngine.compute_signature(
            payload_bytes, "s3cret"
        )
        assert headers["X-Webhook-Signature"] == expected_sig

    async def test_includes_custom_headers(self) -> None:
        mock_client = _make_mock_client(return_value=_ok_response())

        engine = WebhookDeliveryEngine(http_client=mock_client)
        config = WebhookConfig(
            name="h1",
            url="https://example.com/hook",
            headers={"X-Custom": "val"},
        )
        await engine.deliver(config, "e", {})

        call_kwargs = mock_client.post.call_args
        assert call_kwargs.kwargs["headers"]["X-Custom"] == "val"

    async def test_retry_on_failure_then_succeed(self) -> None:
        mock_client = _make_mock_client(
            side_effect=[_fail_response(), _fail_response(), _ok_response()]
        )

        engine = WebhookDeliveryEngine(http_client=mock_client)
        config = WebhookConfig(
            name="h1", url="https://example.com/hook", max_retries=3
        )

        with patch("openclaw_sdk.webhooks.manager.asyncio.sleep", new_callable=AsyncMock):
            delivery = await engine.deliver(config, "evt", {"k": "v"})

        assert delivery.status == DeliveryStatus.SUCCESS
        assert delivery.attempts == 3
        assert delivery.response_status == 200

    async def test_max_retries_exhausted(self) -> None:
        mock_client = _make_mock_client(return_value=_fail_response(502))

        engine = WebhookDeliveryEngine(http_client=mock_client)
        config = WebhookConfig(
            name="h1", url="https://example.com/hook", max_retries=2
        )

        with patch("openclaw_sdk.webhooks.manager.asyncio.sleep", new_callable=AsyncMock):
            delivery = await engine.deliver(config, "evt", {})

        assert delivery.status == DeliveryStatus.FAILED
        assert delivery.attempts == 3  # 1 initial + 2 retries
        assert delivery.error == "HTTP 502"

    async def test_http_error_retries(self) -> None:
        mock_client = _make_mock_client(
            side_effect=[httpx.ConnectError("refused"), _ok_response()]
        )

        engine = WebhookDeliveryEngine(http_client=mock_client)
        config = WebhookConfig(
            name="h1", url="https://example.com/hook", max_retries=2
        )

        with patch("openclaw_sdk.webhooks.manager.asyncio.sleep", new_callable=AsyncMock):
            delivery = await engine.deliver(config, "evt", {})

        assert delivery.status == DeliveryStatus.SUCCESS
        assert delivery.attempts == 2


# ---------------------------------------------------------------------------
# WebhookManager tests
# ---------------------------------------------------------------------------


class TestWebhookManager:
    def test_register_and_list(self) -> None:
        mgr = WebhookManager()
        cfg = WebhookConfig(name="hook1", url="https://a.com")
        result = mgr.register(cfg)
        assert result.name == "hook1"
        assert len(mgr.list_webhooks()) == 1
        assert mgr.list_webhooks()[0].name == "hook1"

    def test_register_duplicate_raises(self) -> None:
        mgr = WebhookManager()
        cfg = WebhookConfig(name="dup", url="https://a.com")
        mgr.register(cfg)
        with pytest.raises(ValueError, match="already registered"):
            mgr.register(cfg)

    def test_unregister(self) -> None:
        mgr = WebhookManager()
        cfg = WebhookConfig(name="hook1", url="https://a.com")
        mgr.register(cfg)
        assert mgr.unregister("hook1") is True
        assert mgr.list_webhooks() == []

    def test_unregister_missing_returns_false(self) -> None:
        mgr = WebhookManager()
        assert mgr.unregister("nope") is False

    def test_get_existing(self) -> None:
        mgr = WebhookManager()
        cfg = WebhookConfig(name="hook1", url="https://a.com")
        mgr.register(cfg)
        assert mgr.get("hook1") is not None
        assert mgr.get("hook1") == cfg

    def test_get_missing_returns_none(self) -> None:
        mgr = WebhookManager()
        assert mgr.get("nope") is None

    async def test_fire_event_to_matching_webhooks(self) -> None:
        mock_client = _make_mock_client(return_value=_ok_response())

        mgr = WebhookManager(http_client=mock_client)
        mgr.register(WebhookConfig(name="h1", url="https://a.com", events=["evt.a"]))
        mgr.register(WebhookConfig(name="h2", url="https://b.com", events=["evt.b"]))

        deliveries = await mgr.fire("evt.a", {"k": "v"})
        assert len(deliveries) == 1
        assert deliveries[0].webhook_name == "h1"
        assert deliveries[0].status == DeliveryStatus.SUCCESS

    async def test_fire_empty_events_matches_all(self) -> None:
        mock_client = _make_mock_client(return_value=_ok_response())

        mgr = WebhookManager(http_client=mock_client)
        mgr.register(WebhookConfig(name="catch-all", url="https://a.com", events=[]))
        mgr.register(WebhookConfig(name="specific", url="https://b.com", events=["other"]))

        deliveries = await mgr.fire("any.event", {})
        assert len(deliveries) == 1
        assert deliveries[0].webhook_name == "catch-all"

    async def test_fire_skips_disabled_webhooks(self) -> None:
        mock_client = _make_mock_client(return_value=_ok_response())

        mgr = WebhookManager(http_client=mock_client)
        mgr.register(
            WebhookConfig(name="disabled", url="https://a.com", enabled=False)
        )
        mgr.register(WebhookConfig(name="enabled", url="https://b.com"))

        deliveries = await mgr.fire("evt", {})
        assert len(deliveries) == 1
        assert deliveries[0].webhook_name == "enabled"

    async def test_get_deliveries_all(self) -> None:
        mock_client = _make_mock_client(return_value=_ok_response())

        mgr = WebhookManager(http_client=mock_client)
        mgr.register(WebhookConfig(name="h1", url="https://a.com"))
        mgr.register(WebhookConfig(name="h2", url="https://b.com"))

        await mgr.fire("evt", {})
        all_deliveries = mgr.get_deliveries()
        assert len(all_deliveries) == 2

    async def test_get_deliveries_with_filter(self) -> None:
        mock_client = _make_mock_client(return_value=_ok_response())

        mgr = WebhookManager(http_client=mock_client)
        mgr.register(WebhookConfig(name="h1", url="https://a.com"))
        mgr.register(WebhookConfig(name="h2", url="https://b.com"))

        await mgr.fire("evt", {})
        filtered = mgr.get_deliveries(webhook_name="h1")
        assert len(filtered) == 1
        assert filtered[0].webhook_name == "h1"

    async def test_retry_failed(self) -> None:
        mock_client = _make_mock_client(return_value=_fail_response())

        mgr = WebhookManager(http_client=mock_client)
        mgr.register(
            WebhookConfig(name="h1", url="https://a.com", max_retries=0)
        )

        with patch("openclaw_sdk.webhooks.manager.asyncio.sleep", new_callable=AsyncMock):
            deliveries = await mgr.fire("evt.fail", {"data": 1})

        assert len(deliveries) == 1
        assert deliveries[0].status == DeliveryStatus.FAILED

        # Now mock returns 200 for retry
        mock_client.post = AsyncMock(return_value=_ok_response())
        retries = await mgr.retry_failed("h1")
        assert len(retries) == 1
        assert retries[0].status == DeliveryStatus.SUCCESS

    async def test_retry_failed_no_webhook_returns_empty(self) -> None:
        mgr = WebhookManager()
        result = await mgr.retry_failed("nonexistent")
        assert result == []
