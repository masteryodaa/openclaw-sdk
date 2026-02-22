# Alerting

The OpenClaw SDK provides a rule-based alerting system that monitors agent
execution results and fires alerts when configurable thresholds are breached.
Alerts are delivered through pluggable sinks (log, webhook, Slack, PagerDuty)
and protected by per-rule cooldown periods to prevent alert flooding.

## Quick Start

```python
import asyncio

from openclaw_sdk import OpenClawClient
from openclaw_sdk.alerting import (
    AlertManager,
    CostThresholdRule,
    LatencyThresholdRule,
    LogAlertSink,
    SlackAlertSink,
)


async def main():
    # Build the alert manager with rules and sinks
    alerts = (
        AlertManager()
        .add_rule(CostThresholdRule(threshold_usd=0.10))
        .add_rule(LatencyThresholdRule(threshold_ms=5000))
        .add_sink(LogAlertSink())
        .add_sink(SlackAlertSink(webhook_url="https://hooks.slack.com/services/..."))
        .set_cooldown(30.0)
    )

    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        agent = client.get_agent("assistant")
        result = await agent.execute("Summarize this 50-page document")

        # Evaluate the result against all rules
        fired = await alerts.evaluate("assistant", result)
        for alert in fired:
            print(f"[{alert.severity.value}] {alert.title}: {alert.message}")

asyncio.run(main())
```

## Alert Model

Every alert is represented by an `Alert` Pydantic model:

```python
from openclaw_sdk.alerting import Alert, AlertSeverity

alert = Alert(
    severity=AlertSeverity.WARNING,
    title="Cost threshold exceeded",
    message="Estimated cost $0.1500 exceeds threshold $0.1000",
    agent_id="assistant",
    rule_name="cost_threshold",
    metadata={"estimated_cost_usd": 0.15, "threshold_usd": 0.10},
)
```

| Field       | Type                     | Default        | Description                            |
|-------------|--------------------------|----------------|----------------------------------------|
| `alert_id`  | `str`                    | Auto-generated | 12-character hex identifier            |
| `severity`  | `AlertSeverity`          | --             | `INFO`, `WARNING`, or `CRITICAL`       |
| `title`     | `str`                    | --             | Brief summary of the alert             |
| `message`   | `str`                    | --             | Detailed description                   |
| `agent_id`  | `str \| None`            | `None`         | Agent that triggered the alert         |
| `rule_name` | `str`                    | `""`           | Name of the rule that fired            |
| `timestamp` | `datetime`               | Now (UTC)      | When the alert was generated           |
| `metadata`  | `dict[str, Any]`         | `{}`           | Arbitrary key-value context            |

### AlertSeverity

`AlertSeverity` is a `StrEnum` with three levels:

| Value      | String       | Typical use                          |
|------------|--------------|--------------------------------------|
| `INFO`     | `"info"`     | Informational, no action needed      |
| `WARNING`  | `"warning"`  | Approaching a limit, investigate     |
| `CRITICAL` | `"critical"` | Threshold breached, immediate action |

## Alert Rules

Rules evaluate an `ExecutionResult` and optionally return an `Alert`. All rules
extend the `AlertRule` ABC:

```python
from openclaw_sdk.alerting import AlertRule, Alert
from openclaw_sdk.core.types import ExecutionResult

class MyCustomRule(AlertRule):
    @property
    def name(self) -> str:
        return "my_custom_rule"

    async def evaluate(self, agent_id: str, result: ExecutionResult) -> Alert | None:
        if some_condition(result):
            return Alert(severity=AlertSeverity.WARNING, title="...", message="...")
        return None
```

### CostThresholdRule

Fires when the estimated execution cost exceeds a USD threshold. Cost is
calculated as `(input_tokens + output_tokens) / 1,000,000 * rate_per_million`.

```python
from openclaw_sdk.alerting import CostThresholdRule, AlertSeverity

rule = CostThresholdRule(
    threshold_usd=0.05,
    severity=AlertSeverity.CRITICAL,
    rate_per_million=15.0,
)
```

| Parameter          | Type             | Default                  | Description                          |
|--------------------|------------------|--------------------------|--------------------------------------|
| `threshold_usd`    | `float`          | --                       | USD cost threshold to trigger alert  |
| `severity`         | `AlertSeverity`  | `AlertSeverity.WARNING`  | Severity of the generated alert      |
| `rate_per_million` | `float`          | `10.0`                   | Price per million tokens (USD)       |

### LatencyThresholdRule

Fires when execution latency exceeds a threshold in milliseconds.

```python
from openclaw_sdk.alerting import LatencyThresholdRule

rule = LatencyThresholdRule(threshold_ms=3000, severity=AlertSeverity.WARNING)
```

| Parameter      | Type             | Default                 | Description                               |
|----------------|------------------|-------------------------|-------------------------------------------|
| `threshold_ms` | `int`            | --                      | Latency threshold in milliseconds         |
| `severity`     | `AlertSeverity`  | `AlertSeverity.WARNING` | Severity of the generated alert           |

### ErrorRateRule

Fires when the failure rate within a sliding window exceeds a percentage
threshold. The rule maintains an internal window of recent results and only
evaluates once the window is full.

```python
from openclaw_sdk.alerting import ErrorRateRule

rule = ErrorRateRule(
    threshold=0.5,    # 50% error rate
    window_size=10,   # Over the last 10 executions
    severity=AlertSeverity.CRITICAL,
)
```

| Parameter     | Type             | Default                  | Description                               |
|---------------|------------------|--------------------------|-------------------------------------------|
| `threshold`   | `float`          | `0.5`                    | Error rate (0.0-1.0) to trigger alert     |
| `window_size` | `int`            | `10`                     | Number of recent results in the window    |
| `severity`    | `AlertSeverity`  | `AlertSeverity.CRITICAL` | Severity of the generated alert           |

!!! tip "Window must be full"
    The `ErrorRateRule` does not fire until the window is completely filled.
    With `window_size=10`, the first 9 executions never produce an alert
    regardless of how many fail.

### ConsecutiveFailureRule

Fires after N consecutive failures. The counter resets to zero on any
successful execution.

```python
from openclaw_sdk.alerting import ConsecutiveFailureRule

rule = ConsecutiveFailureRule(threshold=3, severity=AlertSeverity.CRITICAL)
```

| Parameter   | Type             | Default                  | Description                                    |
|-------------|------------------|--------------------------|------------------------------------------------|
| `threshold` | `int`            | `3`                      | Number of consecutive failures before alerting |
| `severity`  | `AlertSeverity`  | `AlertSeverity.CRITICAL` | Severity of the generated alert                |

## Alert Sinks

Sinks deliver alerts to external systems. All sinks implement the `AlertSink`
ABC with a single `send(alert) -> bool` method. Return `True` on success,
`False` on failure.

### LogAlertSink

Logs alerts via `structlog`. Requires no configuration and no external
dependencies -- useful as a default sink or for development.

```python
from openclaw_sdk.alerting import LogAlertSink

sink = LogAlertSink()
```

### WebhookAlertSink

Sends alerts as JSON via HTTP POST to any URL. Uses `httpx` under the hood.

```python
from openclaw_sdk.alerting import WebhookAlertSink

sink = WebhookAlertSink(
    url="https://my-monitoring.example.com/alerts",
    headers={"Authorization": "Bearer my-token"},
)
```

| Parameter | Type                     | Default | Description                    |
|-----------|--------------------------|---------|--------------------------------|
| `url`     | `str`                    | --      | Target URL for the HTTP POST   |
| `headers` | `dict[str, str] \| None` | `None`  | Additional HTTP headers        |

The alert payload is the full `Alert` model serialized as JSON.

### SlackAlertSink

Posts formatted messages to a Slack channel via an incoming webhook URL.
Messages include severity-appropriate emoji and the agent ID when available.

```python
from openclaw_sdk.alerting import SlackAlertSink

sink = SlackAlertSink(webhook_url="https://hooks.slack.com/services/T.../B.../xxx")
```

| Parameter     | Type  | Default | Description                       |
|---------------|-------|---------|-----------------------------------|
| `webhook_url` | `str` | --      | Slack incoming webhook URL        |

### PagerDutyAlertSink

Creates incidents in PagerDuty via the Events API v2. Alert severity maps
directly to PagerDuty severity levels. A deduplication key is generated from
the rule name and agent ID.

```python
from openclaw_sdk.alerting import PagerDutyAlertSink

sink = PagerDutyAlertSink(routing_key="your-pagerduty-routing-key")
```

| Parameter     | Type  | Default | Description                       |
|---------------|-------|---------|-----------------------------------|
| `routing_key` | `str` | --      | PagerDuty Events API routing key  |

!!! tip "Custom sinks"
    To deliver alerts to a system not covered by the built-in sinks, extend
    `AlertSink` and implement `send()`:

    ```python
    class EmailAlertSink(AlertSink):
        async def send(self, alert: Alert) -> bool:
            # Send email via your SMTP provider
            ...
            return True
    ```

## AlertManager

`AlertManager` ties rules and sinks together with a fluent builder API. On each
call to `evaluate()`, it runs every rule against the execution result, applies
cooldown logic, and dispatches any fired alerts to all sinks.

```python
from openclaw_sdk.alerting import (
    AlertManager,
    ConsecutiveFailureRule,
    CostThresholdRule,
    ErrorRateRule,
    LatencyThresholdRule,
    LogAlertSink,
    WebhookAlertSink,
)

manager = (
    AlertManager()
    .add_rule(CostThresholdRule(threshold_usd=0.10))
    .add_rule(LatencyThresholdRule(threshold_ms=5000))
    .add_rule(ErrorRateRule(threshold=0.3, window_size=20))
    .add_rule(ConsecutiveFailureRule(threshold=5))
    .add_sink(LogAlertSink())
    .add_sink(WebhookAlertSink(url="https://alerts.example.com/webhook"))
    .set_cooldown(60.0)
)
```

| Method              | Returns         | Description                                   |
|---------------------|-----------------|-----------------------------------------------|
| `add_rule(rule)`    | `AlertManager`  | Add an alert rule (chainable)                 |
| `add_sink(sink)`    | `AlertManager`  | Add an alert sink (chainable)                 |
| `set_cooldown(sec)` | `AlertManager`  | Set per-rule cooldown in seconds (chainable)  |
| `evaluate(agent_id, result)` | `list[Alert]` | Evaluate all rules and dispatch alerts  |

### Cooldown Behaviour

By default, the cooldown period is **60 seconds**. When a rule fires, it will
not fire again for that many seconds, even if subsequent execution results still
breach the threshold. This prevents alert storms during sustained incidents.

```python
# Suppress duplicate alerts for 2 minutes
manager.set_cooldown(120.0)
```

!!! warning "Cooldown is per-rule, not per-agent"
    The cooldown timer is keyed by rule name, not by `(rule, agent)`. If you
    monitor multiple agents through the same `AlertManager`, a cooldown
    triggered by one agent suppresses alerts from all agents for that rule.

## Full Example: Production Monitoring

```python
import asyncio

from openclaw_sdk import OpenClawClient
from openclaw_sdk.alerting import (
    AlertManager,
    ConsecutiveFailureRule,
    CostThresholdRule,
    ErrorRateRule,
    LatencyThresholdRule,
    LogAlertSink,
    PagerDutyAlertSink,
    SlackAlertSink,
)


async def main():
    manager = (
        AlertManager()
        # Rules
        .add_rule(CostThresholdRule(threshold_usd=0.50, rate_per_million=15.0))
        .add_rule(LatencyThresholdRule(threshold_ms=10000))
        .add_rule(ErrorRateRule(threshold=0.25, window_size=20))
        .add_rule(ConsecutiveFailureRule(threshold=3))
        # Sinks
        .add_sink(LogAlertSink())
        .add_sink(SlackAlertSink(webhook_url="https://hooks.slack.com/services/..."))
        .add_sink(PagerDutyAlertSink(routing_key="your-key"))
        # Cooldown
        .set_cooldown(120.0)
    )

    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        agent = client.get_agent("assistant")

        queries = [
            "Summarize this report",
            "Translate to French",
            "Extract key metrics",
        ]

        for query in queries:
            result = await agent.execute(query)
            alerts = await manager.evaluate("assistant", result)

            if alerts:
                print(f"{len(alerts)} alert(s) fired for: {query}")
            else:
                print(f"No alerts for: {query}")

asyncio.run(main())
```
