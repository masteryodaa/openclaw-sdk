"""Alerting system for monitoring agent execution."""
from __future__ import annotations

from openclaw_sdk.alerting.manager import AlertManager
from openclaw_sdk.alerting.models import Alert, AlertSeverity
from openclaw_sdk.alerting.rules import (
    AlertRule,
    ConsecutiveFailureRule,
    CostThresholdRule,
    ErrorRateRule,
    LatencyThresholdRule,
)
from openclaw_sdk.alerting.sinks import (
    AlertSink,
    LogAlertSink,
    PagerDutyAlertSink,
    SlackAlertSink,
    WebhookAlertSink,
)

__all__ = [
    "Alert",
    "AlertManager",
    "AlertRule",
    "AlertSeverity",
    "AlertSink",
    "ConsecutiveFailureRule",
    "CostThresholdRule",
    "ErrorRateRule",
    "LatencyThresholdRule",
    "LogAlertSink",
    "PagerDutyAlertSink",
    "SlackAlertSink",
    "WebhookAlertSink",
]
