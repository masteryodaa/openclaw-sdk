"""Tests for webhooks/manager.py — WebhookManager stub."""
from __future__ import annotations

import pytest

from openclaw_sdk.webhooks.manager import WebhookConfig, WebhookManager


async def test_list_webhooks_raises_not_implemented() -> None:
    mgr = WebhookManager()
    with pytest.raises(NotImplementedError, match="CLI"):
        await mgr.list_webhooks()


async def test_create_webhook_raises_not_implemented() -> None:
    mgr = WebhookManager()
    config = WebhookConfig(name="test", url="https://example.com/hook")
    with pytest.raises(NotImplementedError, match="CLI"):
        await mgr.create_webhook(config)


async def test_delete_webhook_raises_not_implemented() -> None:
    mgr = WebhookManager()
    with pytest.raises(NotImplementedError, match="CLI"):
        await mgr.delete_webhook("hook-123")
