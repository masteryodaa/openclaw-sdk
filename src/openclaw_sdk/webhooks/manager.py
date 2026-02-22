"""Webhook manager — register webhooks, fire events, deliver with retries."""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

import httpx
import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class WebhookConfig(BaseModel):
    """Configuration for a registered webhook endpoint."""

    name: str
    url: str
    events: list[str] = Field(default_factory=list)
    secret: str | None = None
    enabled: bool = True
    max_retries: int = 3
    timeout_seconds: float = 10.0
    headers: dict[str, str] = Field(default_factory=dict)


class DeliveryStatus(StrEnum):
    """Status of a webhook delivery attempt."""

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


class WebhookDelivery(BaseModel):
    """Tracks the lifecycle of a single webhook delivery."""

    delivery_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    webhook_name: str
    event_type: str
    status: DeliveryStatus = DeliveryStatus.PENDING
    attempts: int = 0
    max_attempts: int = 1
    response_status: int | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_attempt_at: datetime | None = None


class WebhookDeliveryEngine:
    """Handles the actual HTTP delivery of webhook payloads with retries."""

    def __init__(self, http_client: httpx.AsyncClient | None = None) -> None:
        self._http_client = http_client

    @staticmethod
    def compute_signature(payload_bytes: bytes, secret: str) -> str:
        """Compute HMAC-SHA256 signature for a webhook payload."""
        return hmac.new(
            secret.encode("utf-8"),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()

    async def deliver(
        self,
        config: WebhookConfig,
        event_type: str,
        payload: dict[str, Any],
    ) -> WebhookDelivery:
        """Deliver a webhook payload with retries on failure.

        Uses exponential backoff: 1s, 2s, 4s, ... between attempts.
        """
        max_attempts = config.max_retries + 1
        delivery = WebhookDelivery(
            webhook_name=config.name,
            event_type=event_type,
            max_attempts=max_attempts,
        )

        payload_bytes = json.dumps(payload, default=str).encode("utf-8")

        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "X-Webhook-Event": event_type,
            **config.headers,
        }
        if config.secret:
            signature = self.compute_signature(payload_bytes, config.secret)
            headers["X-Webhook-Signature"] = signature

        should_close = False
        client = self._http_client
        if client is None:
            client = httpx.AsyncClient()
            should_close = True

        try:
            for attempt in range(max_attempts):
                delivery.attempts = attempt + 1
                delivery.last_attempt_at = datetime.now(timezone.utc)

                if attempt > 0:
                    delivery.status = DeliveryStatus.RETRYING

                try:
                    response = await client.post(
                        config.url,
                        content=payload_bytes,
                        headers=headers,
                        timeout=config.timeout_seconds,
                    )
                    delivery.response_status = response.status_code

                    if 200 <= response.status_code < 300:
                        delivery.status = DeliveryStatus.SUCCESS
                        logger.info(
                            "webhook_delivered",
                            webhook=config.name,
                            event_type=event_type,
                            status=response.status_code,
                            attempts=delivery.attempts,
                        )
                        return delivery

                    # Non-2xx — treat as failure, retry if attempts remain
                    delivery.error = (
                        f"HTTP {response.status_code}"
                    )
                    logger.warning(
                        "webhook_delivery_failed",
                        webhook=config.name,
                        event_type=event_type,
                        status=response.status_code,
                        attempt=delivery.attempts,
                    )

                except httpx.HTTPError as exc:
                    delivery.error = str(exc)
                    logger.warning(
                        "webhook_delivery_error",
                        webhook=config.name,
                        event_type=event_type,
                        error=str(exc),
                        attempt=delivery.attempts,
                    )

                # Exponential backoff before next attempt (if any remain)
                if attempt < max_attempts - 1:
                    backoff = 2**attempt  # 1, 2, 4, 8, ...
                    await asyncio.sleep(backoff)

            # All attempts exhausted
            delivery.status = DeliveryStatus.FAILED
            logger.error(
                "webhook_delivery_exhausted",
                webhook=config.name,
                event_type=event_type,
                attempts=delivery.attempts,
                max_attempts=max_attempts,
            )
            return delivery
        finally:
            if should_close:
                await client.aclose()


class WebhookManager:
    """Manages webhook registration, event firing, and delivery tracking."""

    def __init__(
        self,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._webhooks: dict[str, WebhookConfig] = {}
        self._deliveries: list[WebhookDelivery] = []
        self._engine = WebhookDeliveryEngine(http_client=http_client)

    def register(self, config: WebhookConfig) -> WebhookConfig:
        """Register a webhook. Raises ValueError on duplicate name."""
        if config.name in self._webhooks:
            msg = f"Webhook '{config.name}' is already registered"
            raise ValueError(msg)
        self._webhooks[config.name] = config
        logger.info("webhook_registered", name=config.name, url=config.url)
        return config

    def unregister(self, name: str) -> bool:
        """Unregister a webhook by name. Returns True if found and removed."""
        if name in self._webhooks:
            del self._webhooks[name]
            logger.info("webhook_unregistered", name=name)
            return True
        return False

    def get(self, name: str) -> WebhookConfig | None:
        """Get a webhook configuration by name."""
        return self._webhooks.get(name)

    def list_webhooks(self) -> list[WebhookConfig]:
        """List all registered webhooks."""
        return list(self._webhooks.values())

    async def fire(
        self,
        event_type: str,
        payload: dict[str, Any],
    ) -> list[WebhookDelivery]:
        """Fire an event to all matching, enabled webhooks.

        A webhook matches if its events list contains event_type,
        or if its events list is empty (matches all events).
        Disabled webhooks are skipped.
        """
        deliveries: list[WebhookDelivery] = []
        for config in self._webhooks.values():
            if not config.enabled:
                continue
            if config.events and event_type not in config.events:
                continue

            delivery = await self._engine.deliver(config, event_type, payload)
            self._deliveries.append(delivery)
            deliveries.append(delivery)

        return deliveries

    def get_deliveries(
        self,
        *,
        webhook_name: str | None = None,
        limit: int = 100,
    ) -> list[WebhookDelivery]:
        """Get delivery history, optionally filtered by webhook name."""
        result = self._deliveries
        if webhook_name is not None:
            result = [d for d in result if d.webhook_name == webhook_name]
        return result[-limit:]

    async def retry_failed(self, webhook_name: str) -> list[WebhookDelivery]:
        """Retry all failed deliveries for a given webhook.

        Returns list of new delivery attempts.
        """
        config = self._webhooks.get(webhook_name)
        if config is None:
            return []

        failed = [
            d
            for d in self._deliveries
            if d.webhook_name == webhook_name and d.status == DeliveryStatus.FAILED
        ]

        new_deliveries: list[WebhookDelivery] = []
        for old_delivery in failed:
            delivery = await self._engine.deliver(
                config, old_delivery.event_type, {}
            )
            self._deliveries.append(delivery)
            new_deliveries.append(delivery)

        return new_deliveries
