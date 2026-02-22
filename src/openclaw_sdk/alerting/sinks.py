"""Alert sinks for delivering alerts to various destinations."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import structlog

from openclaw_sdk.alerting.models import Alert

logger = structlog.get_logger(__name__)


class AlertSink(ABC):
    """Base class for alert delivery sinks."""

    @abstractmethod
    async def send(self, alert: Alert) -> bool:
        """Send an alert. Return ``True`` on success, ``False`` on failure."""
        ...


class LogAlertSink(AlertSink):
    """Logs alerts via structlog. Always available, no external dependencies."""

    async def send(self, alert: Alert) -> bool:
        """Log the alert at the appropriate level based on severity."""
        logger.warning(
            "alert_fired",
            alert_id=alert.alert_id,
            severity=alert.severity.value,
            title=alert.title,
            message=alert.message,
            agent_id=alert.agent_id,
            rule_name=alert.rule_name,
        )
        return True


class WebhookAlertSink(AlertSink):
    """Sends alerts via HTTP POST using httpx."""

    def __init__(self, url: str, headers: dict[str, str] | None = None) -> None:
        self._url = url
        self._headers = headers or {}

    async def send(self, alert: Alert) -> bool:
        """POST the alert as JSON to the configured URL."""
        import httpx

        payload = alert.model_dump(mode="json")
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    self._url,
                    json=payload,
                    headers=self._headers,
                    timeout=10.0,
                )
                return resp.status_code < 400  # noqa: PLR2004
        except Exception as exc:  # noqa: BLE001
            logger.error("webhook_sink_error", url=self._url, error=str(exc))
            return False


class SlackAlertSink(AlertSink):
    """Sends alerts to Slack via an incoming webhook URL."""

    def __init__(self, webhook_url: str) -> None:
        self._webhook_url = webhook_url

    async def send(self, alert: Alert) -> bool:
        """Format and POST the alert as a Slack message."""
        import httpx

        severity_emoji: dict[str, str] = {
            "info": ":information_source:",
            "warning": ":warning:",
            "critical": ":rotating_light:",
        }
        emoji = severity_emoji.get(alert.severity.value, ":bell:")
        text = (
            f"{emoji} *[{alert.severity.value.upper()}] {alert.title}*\n"
            f"{alert.message}"
        )
        if alert.agent_id:
            text += f"\nAgent: `{alert.agent_id}`"

        payload: dict[str, Any] = {"text": text}
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    self._webhook_url,
                    json=payload,
                    timeout=10.0,
                )
                return resp.status_code < 400  # noqa: PLR2004
        except Exception as exc:  # noqa: BLE001
            logger.error("slack_sink_error", error=str(exc))
            return False


class PagerDutyAlertSink(AlertSink):
    """Sends alerts to PagerDuty Events API v2."""

    EVENTS_URL = "https://events.pagerduty.com/v2/enqueue"

    def __init__(self, routing_key: str) -> None:
        self._routing_key = routing_key

    async def send(self, alert: Alert) -> bool:
        """Create a PagerDuty event from the alert."""
        import httpx

        severity_map: dict[str, str] = {
            "info": "info",
            "warning": "warning",
            "critical": "critical",
        }
        pd_severity = severity_map.get(alert.severity.value, "warning")

        payload: dict[str, Any] = {
            "routing_key": self._routing_key,
            "event_action": "trigger",
            "payload": {
                "summary": f"[{alert.severity.value.upper()}] {alert.title}: {alert.message}",
                "severity": pd_severity,
                "source": f"openclaw-sdk:{alert.agent_id or 'unknown'}",
                "custom_details": alert.metadata,
            },
            "dedup_key": f"openclaw-{alert.rule_name}-{alert.agent_id or 'global'}",
        }
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    self.EVENTS_URL,
                    json=payload,
                    timeout=10.0,
                )
                return resp.status_code < 400  # noqa: PLR2004
        except Exception as exc:  # noqa: BLE001
            logger.error("pagerduty_sink_error", error=str(exc))
            return False
