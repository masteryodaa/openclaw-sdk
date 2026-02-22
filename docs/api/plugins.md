# Plugins & Alerting

Plugin system for extending the SDK, and alerting system for monitoring agent execution.

## Plugins

### Plugin

::: openclaw_sdk.plugins.base.Plugin
    options:
      show_source: true
      heading_level: 4

### PluginHook

::: openclaw_sdk.plugins.base.PluginHook
    options:
      show_source: true
      heading_level: 4

### PluginMetadata

::: openclaw_sdk.plugins.base.PluginMetadata
    options:
      show_source: true
      heading_level: 4

### PluginRegistry

::: openclaw_sdk.plugins.registry.PluginRegistry
    options:
      show_source: true
      heading_level: 4

### HookManager

::: openclaw_sdk.plugins.hooks.HookManager
    options:
      show_source: true
      heading_level: 4

## Alerting

### AlertManager

::: openclaw_sdk.alerting.manager.AlertManager
    options:
      show_source: true
      heading_level: 4

### AlertRule

::: openclaw_sdk.alerting.rules.AlertRule
    options:
      show_source: true
      heading_level: 4

### AlertSink

::: openclaw_sdk.alerting.sinks.AlertSink
    options:
      show_source: true
      heading_level: 4

### Alert

::: openclaw_sdk.alerting.models.Alert
    options:
      show_source: true
      heading_level: 4

### AlertSeverity

::: openclaw_sdk.alerting.models.AlertSeverity
    options:
      show_source: true
      heading_level: 4

### Built-in Rules

#### CostThresholdRule

::: openclaw_sdk.alerting.rules.CostThresholdRule
    options:
      show_source: true
      heading_level: 5

#### ErrorRateRule

::: openclaw_sdk.alerting.rules.ErrorRateRule
    options:
      show_source: true
      heading_level: 5

#### LatencyThresholdRule

::: openclaw_sdk.alerting.rules.LatencyThresholdRule
    options:
      show_source: true
      heading_level: 5

#### ConsecutiveFailureRule

::: openclaw_sdk.alerting.rules.ConsecutiveFailureRule
    options:
      show_source: true
      heading_level: 5

### Built-in Sinks

#### LogAlertSink

::: openclaw_sdk.alerting.sinks.LogAlertSink
    options:
      show_source: true
      heading_level: 5

#### WebhookAlertSink

::: openclaw_sdk.alerting.sinks.WebhookAlertSink
    options:
      show_source: true
      heading_level: 5

#### SlackAlertSink

::: openclaw_sdk.alerting.sinks.SlackAlertSink
    options:
      show_source: true
      heading_level: 5

#### PagerDutyAlertSink

::: openclaw_sdk.alerting.sinks.PagerDutyAlertSink
    options:
      show_source: true
      heading_level: 5
