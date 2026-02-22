"""Tests for alerting/ — rules, sinks, and manager."""
from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
import pytest

from openclaw_sdk.alerting.manager import AlertManager
from openclaw_sdk.alerting.models import Alert, AlertSeverity
from openclaw_sdk.alerting.rules import (
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
from openclaw_sdk.core.types import ExecutionResult, TokenUsage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_result(
    success: bool = True,
    latency_ms: int = 100,
    input_tokens: int = 100,
    output_tokens: int = 50,
) -> ExecutionResult:
    return ExecutionResult(
        success=success,
        content="test",
        latency_ms=latency_ms,
        token_usage=TokenUsage(input=input_tokens, output=output_tokens),
    )


def _make_alert(severity: AlertSeverity = AlertSeverity.WARNING) -> Alert:
    return Alert(
        severity=severity,
        title="Test Alert",
        message="Something happened",
        agent_id="agent1",
        rule_name="test_rule",
    )


class RecordingSink(AlertSink):
    """Sink that records all alerts for testing."""

    def __init__(self) -> None:
        self.alerts: list[Alert] = []

    async def send(self, alert: Alert) -> bool:
        self.alerts.append(alert)
        return True


class BrokenSink(AlertSink):
    """Sink that always raises."""

    async def send(self, alert: Alert) -> bool:
        raise RuntimeError("sink exploded")


# ---------------------------------------------------------------------------
# CostThresholdRule
# ---------------------------------------------------------------------------


async def test_cost_threshold_fires() -> None:
    # 1000 input + 500 output = 1500 tokens at $10/M = $0.015
    rule = CostThresholdRule(threshold_usd=0.01, rate_per_million=10.0)
    result = _make_result(input_tokens=1000, output_tokens=500)
    alert = await rule.evaluate("agent1", result)
    assert alert is not None
    assert alert.severity == AlertSeverity.WARNING
    assert "exceeds" in alert.message
    assert alert.rule_name == "cost_threshold"


async def test_cost_threshold_no_fire() -> None:
    rule = CostThresholdRule(threshold_usd=1.0, rate_per_million=10.0)
    result = _make_result(input_tokens=100, output_tokens=50)
    alert = await rule.evaluate("agent1", result)
    assert alert is None


# ---------------------------------------------------------------------------
# LatencyThresholdRule
# ---------------------------------------------------------------------------


async def test_latency_threshold_fires() -> None:
    rule = LatencyThresholdRule(threshold_ms=500)
    result = _make_result(latency_ms=1000)
    alert = await rule.evaluate("agent1", result)
    assert alert is not None
    assert "1000ms" in alert.message
    assert alert.rule_name == "latency_threshold"


async def test_latency_threshold_no_fire() -> None:
    rule = LatencyThresholdRule(threshold_ms=5000)
    result = _make_result(latency_ms=100)
    alert = await rule.evaluate("agent1", result)
    assert alert is None


# ---------------------------------------------------------------------------
# ErrorRateRule
# ---------------------------------------------------------------------------


async def test_error_rate_fires() -> None:
    rule = ErrorRateRule(threshold=0.5, window_size=4)

    # Fill window with 3 failures and 1 success -> 75% error rate
    await rule.evaluate("a1", _make_result(success=False))
    await rule.evaluate("a1", _make_result(success=False))
    await rule.evaluate("a1", _make_result(success=False))
    alert = await rule.evaluate("a1", _make_result(success=True))
    # Window: [False, False, False, True] -> 75% failures > 50% threshold
    assert alert is not None
    assert alert.rule_name == "error_rate"
    assert alert.severity == AlertSeverity.CRITICAL


async def test_error_rate_no_fire() -> None:
    rule = ErrorRateRule(threshold=0.5, window_size=4)

    # Fill window with 3 successes and 1 failure -> 25% error rate
    await rule.evaluate("a1", _make_result(success=True))
    await rule.evaluate("a1", _make_result(success=True))
    await rule.evaluate("a1", _make_result(success=True))
    alert = await rule.evaluate("a1", _make_result(success=False))
    # Window: [True, True, True, False] -> 25% failures < 50% threshold
    assert alert is None


# ---------------------------------------------------------------------------
# ConsecutiveFailureRule
# ---------------------------------------------------------------------------


async def test_consecutive_failure_fires() -> None:
    rule = ConsecutiveFailureRule(threshold=3)

    await rule.evaluate("a1", _make_result(success=False))
    await rule.evaluate("a1", _make_result(success=False))
    alert = await rule.evaluate("a1", _make_result(success=False))

    assert alert is not None
    assert "3 consecutive" in alert.message
    assert alert.rule_name == "consecutive_failure"


async def test_consecutive_failure_resets_on_success() -> None:
    rule = ConsecutiveFailureRule(threshold=3)

    await rule.evaluate("a1", _make_result(success=False))
    await rule.evaluate("a1", _make_result(success=False))
    # Reset
    await rule.evaluate("a1", _make_result(success=True))
    # Start again — only 2 failures, not enough
    await rule.evaluate("a1", _make_result(success=False))
    alert = await rule.evaluate("a1", _make_result(success=False))

    assert alert is None


# ---------------------------------------------------------------------------
# Sinks
# ---------------------------------------------------------------------------


async def test_log_sink() -> None:
    sink = LogAlertSink()
    alert = _make_alert()
    result = await sink.send(alert)
    assert result is True


async def test_webhook_sink(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_response = AsyncMock()
    mock_response.status_code = 200

    mock_client_instance = AsyncMock()
    mock_client_instance.post = AsyncMock(return_value=mock_response)
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=None)

    monkeypatch.setattr(httpx, "AsyncClient", lambda: mock_client_instance)

    sink = WebhookAlertSink(url="https://example.com/alerts", headers={"X-Key": "123"})
    alert = _make_alert()
    result = await sink.send(alert)
    assert result is True
    mock_client_instance.post.assert_called_once()


async def test_slack_sink(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_response = AsyncMock()
    mock_response.status_code = 200

    mock_client_instance = AsyncMock()
    mock_client_instance.post = AsyncMock(return_value=mock_response)
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=None)

    monkeypatch.setattr(httpx, "AsyncClient", lambda: mock_client_instance)

    sink = SlackAlertSink(webhook_url="https://hooks.slack.com/services/T/B/X")
    alert = _make_alert()
    result = await sink.send(alert)
    assert result is True
    call_kwargs = mock_client_instance.post.call_args
    payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
    assert "text" in payload


async def test_pagerduty_sink(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_response = AsyncMock()
    mock_response.status_code = 202

    mock_client_instance = AsyncMock()
    mock_client_instance.post = AsyncMock(return_value=mock_response)
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=None)

    monkeypatch.setattr(httpx, "AsyncClient", lambda: mock_client_instance)

    sink = PagerDutyAlertSink(routing_key="test-routing-key")
    alert = _make_alert(severity=AlertSeverity.CRITICAL)
    result = await sink.send(alert)
    assert result is True
    call_kwargs = mock_client_instance.post.call_args
    payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
    assert payload["routing_key"] == "test-routing-key"
    assert payload["payload"]["severity"] == "critical"


# ---------------------------------------------------------------------------
# AlertManager
# ---------------------------------------------------------------------------


async def test_manager_evaluates_all_rules() -> None:
    manager = AlertManager().set_cooldown(0)
    manager.add_rule(CostThresholdRule(threshold_usd=0.0001, rate_per_million=10.0))
    manager.add_rule(LatencyThresholdRule(threshold_ms=50))

    sink = RecordingSink()
    manager.add_sink(sink)

    # Both rules should fire
    result = _make_result(latency_ms=1000, input_tokens=500, output_tokens=500)
    alerts = await manager.evaluate("agent1", result)
    assert len(alerts) == 2
    assert len(sink.alerts) == 2


async def test_manager_dispatches_to_all_sinks() -> None:
    manager = AlertManager().set_cooldown(0)
    manager.add_rule(LatencyThresholdRule(threshold_ms=50))

    sink1 = RecordingSink()
    sink2 = RecordingSink()
    manager.add_sink(sink1)
    manager.add_sink(sink2)

    result = _make_result(latency_ms=1000)
    await manager.evaluate("agent1", result)

    assert len(sink1.alerts) == 1
    assert len(sink2.alerts) == 1


async def test_manager_cooldown_suppresses() -> None:
    manager = AlertManager().set_cooldown(9999)  # very long cooldown
    manager.add_rule(LatencyThresholdRule(threshold_ms=50))

    sink = RecordingSink()
    manager.add_sink(sink)

    result = _make_result(latency_ms=1000)

    # First evaluation: fires
    alerts1 = await manager.evaluate("agent1", result)
    assert len(alerts1) == 1

    # Second evaluation: suppressed by cooldown
    alerts2 = await manager.evaluate("agent1", result)
    assert len(alerts2) == 0

    # Sink should only have received the first alert
    assert len(sink.alerts) == 1


async def test_manager_no_rules() -> None:
    manager = AlertManager()
    sink = RecordingSink()
    manager.add_sink(sink)

    result = _make_result()
    alerts = await manager.evaluate("agent1", result)
    assert alerts == []
    assert sink.alerts == []


async def test_manager_no_sinks() -> None:
    manager = AlertManager().set_cooldown(0)
    manager.add_rule(LatencyThresholdRule(threshold_ms=50))

    result = _make_result(latency_ms=1000)
    # Should not raise even with no sinks
    alerts = await manager.evaluate("agent1", result)
    assert len(alerts) == 1


async def test_sink_error_isolation() -> None:
    """A broken sink should not prevent other sinks from receiving the alert."""
    manager = AlertManager().set_cooldown(0)
    manager.add_rule(LatencyThresholdRule(threshold_ms=50))

    broken = BrokenSink()
    good = RecordingSink()
    manager.add_sink(broken)
    manager.add_sink(good)

    result = _make_result(latency_ms=1000)
    alerts = await manager.evaluate("agent1", result)

    # Alert should still be in the fired list
    assert len(alerts) == 1
    # Good sink should have received it despite broken sink
    assert len(good.alerts) == 1
