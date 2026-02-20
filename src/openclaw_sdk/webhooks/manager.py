from __future__ import annotations

from pydantic import BaseModel, Field


class WebhookConfig(BaseModel):
    name: str
    url: str
    events: list[str] = Field(default_factory=list)
    secret: str | None = None
    enabled: bool = True


class WebhookManager:
    """Stub — webhooks in OpenClaw are platform-specific CLI integrations (e.g. Gmail Pub/Sub).

    There is no generic webhook gateway API in OpenClaw v0.1.
    This class is kept as a placeholder for future implementation.
    """

    async def list_webhooks(self) -> list[WebhookConfig]:
        raise NotImplementedError(
            "OpenClaw webhooks are CLI-only integrations. "
            "Use `openclaw webhooks` CLI commands instead."
        )

    async def create_webhook(self, config: WebhookConfig) -> WebhookConfig:
        raise NotImplementedError(
            "OpenClaw webhooks are CLI-only integrations. "
            "Use `openclaw webhooks` CLI commands instead."
        )

    async def delete_webhook(self, webhook_id: str) -> bool:
        raise NotImplementedError(
            "OpenClaw webhooks are CLI-only integrations. "
            "Use `openclaw webhooks` CLI commands instead."
        )
