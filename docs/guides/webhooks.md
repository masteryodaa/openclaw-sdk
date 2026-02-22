# Webhooks

The OpenClaw SDK includes a webhook delivery system with HMAC-SHA256 payload signing,
automatic retries with exponential backoff, and full delivery tracking. Register
webhook endpoints, fire events, and the `WebhookManager` handles signing, delivery,
retry logic, and status tracking for you.

## Quick Start

```python
import asyncio
from openclaw_sdk.webhooks.manager import WebhookManager, WebhookConfig

async def main():
    manager = WebhookManager()

    # Register a webhook endpoint
    manager.register(WebhookConfig(
        name="my-webhook",
        url="https://example.com/webhook",
        events=["agent.completed", "agent.failed"],
        secret="my-signing-secret",
    ))

    # Fire an event -- delivers to all matching webhooks
    deliveries = await manager.fire("agent.completed", {
        "agent_id": "assistant",
        "result": "Task completed successfully",
    })

    for d in deliveries:
        print(f"{d.webhook_name}: {d.status} (attempts: {d.attempts})")

asyncio.run(main())
```

## WebhookConfig

Each registered webhook is defined by a `WebhookConfig` model. The `name` is the
unique identifier used to manage the webhook.

```python
from openclaw_sdk.webhooks.manager import WebhookConfig

config = WebhookConfig(
    name="slack-notifications",
    url="https://hooks.slack.com/services/...",
    events=["agent.completed", "agent.failed"],
    secret="hmac-secret-key",
    enabled=True,
    max_retries=3,
    timeout_seconds=10.0,
    headers={"X-Custom-Header": "my-value"},
)
```

| Parameter         | Type              | Default | Description                                         |
|-------------------|-------------------|---------|-----------------------------------------------------|
| `name`            | `str`             | *required* | Unique webhook identifier                        |
| `url`             | `str`             | *required* | Endpoint URL to deliver payloads to               |
| `events`          | `list[str]`       | `[]`    | Event types to match; empty list matches all events |
| `secret`          | `str \| None`     | `None`  | HMAC-SHA256 signing secret                          |
| `enabled`         | `bool`            | `True`  | Whether the webhook is active                       |
| `max_retries`     | `int`             | `3`     | Number of retry attempts after the initial delivery |
| `timeout_seconds` | `float`           | `10.0`  | HTTP request timeout in seconds                     |
| `headers`         | `dict[str, str]`  | `{}`    | Additional HTTP headers to include in requests      |

!!! tip "Event filtering"
    When `events` is an empty list, the webhook matches **all** event types. To
    subscribe to specific events only, provide the list of event type strings you
    care about (e.g. `["agent.completed", "session.created"]`).

## WebhookManager

The `WebhookManager` is the central class for registering webhooks, firing events,
and querying delivery history.

```python
from openclaw_sdk.webhooks.manager import WebhookManager

# Create with default settings
manager = WebhookManager()

# Or provide a shared httpx client for connection pooling
import httpx
http_client = httpx.AsyncClient()
manager = WebhookManager(http_client=http_client)
```

| Parameter     | Type                         | Default | Description                            |
|---------------|------------------------------|---------|----------------------------------------|
| `http_client` | `httpx.AsyncClient \| None`  | `None`  | Shared HTTP client for connection pooling |

### Registering Webhooks

```python
config = WebhookConfig(name="my-hook", url="https://example.com/hook")
manager.register(config)
```

Raises `ValueError` if a webhook with the same name is already registered.

### Unregistering Webhooks

```python
removed = manager.unregister("my-hook")
print(removed)  # True if found and removed, False otherwise
```

### Listing Webhooks

```python
hooks = manager.list_webhooks()
for hook in hooks:
    print(f"{hook.name}: {hook.url} (enabled={hook.enabled})")
```

### Getting a Webhook by Name

```python
config = manager.get("my-hook")
if config:
    print(f"URL: {config.url}")
```

### Firing Events

The `fire()` method delivers a payload to all matching, enabled webhooks:

```python
deliveries = await manager.fire("agent.completed", {
    "agent_id": "assistant",
    "session": "main",
    "content": "Task finished",
    "timestamp": "2025-01-15T12:00:00Z",
})

for d in deliveries:
    print(f"{d.webhook_name}: {d.status}")
```

A webhook matches an event if:

1. The webhook is **enabled** (`enabled=True`).
2. The webhook's `events` list contains the `event_type`, **or** the `events` list is
   empty (matches all events).

### Querying Delivery History

```python
# Get all deliveries (most recent last, up to 100)
all_deliveries = manager.get_deliveries()

# Filter by webhook name
hook_deliveries = manager.get_deliveries(webhook_name="my-hook", limit=50)

for d in hook_deliveries:
    print(f"  {d.event_type}: {d.status} ({d.attempts} attempts)")
```

| Parameter      | Type           | Default | Description                              |
|----------------|----------------|---------|------------------------------------------|
| `webhook_name` | `str \| None`  | `None`  | Filter deliveries by webhook name        |
| `limit`        | `int`          | `100`   | Maximum number of deliveries to return   |

### Retrying Failed Deliveries

```python
new_deliveries = await manager.retry_failed("my-hook")
for d in new_deliveries:
    print(f"Retry: {d.status} ({d.attempts} attempts)")
```

The `retry_failed()` method finds all deliveries with `FAILED` status for the
specified webhook and re-attempts delivery using the current webhook configuration.

## WebhookDeliveryEngine

The `WebhookDeliveryEngine` handles the low-level HTTP delivery of webhook payloads.
It is used internally by `WebhookManager`, but you can also use it directly for
custom delivery logic.

### HMAC-SHA256 Signing

When a webhook has a `secret` configured, the engine computes an HMAC-SHA256
signature of the JSON payload and includes it in the `X-Webhook-Signature` header:

```python
from openclaw_sdk.webhooks.manager import WebhookDeliveryEngine

signature = WebhookDeliveryEngine.compute_signature(
    b'{"event": "test"}',
    "my-secret-key",
)
print(signature)  # hex-encoded HMAC-SHA256 digest
```

### Delivery Headers

Every webhook delivery includes these headers:

| Header                 | Description                                   |
|------------------------|-----------------------------------------------|
| `Content-Type`         | Always `application/json`                     |
| `X-Webhook-Event`      | The event type string                         |
| `X-Webhook-Signature`  | HMAC-SHA256 hex digest (only when `secret` is set) |

Any additional headers from `WebhookConfig.headers` are also included.

### Retry Strategy

The engine uses exponential backoff between retry attempts:

| Attempt | Backoff Delay |
|---------|---------------|
| 1st     | 0s (immediate) |
| 2nd     | 1s            |
| 3rd     | 2s            |
| 4th     | 4s            |

The total number of attempts is `max_retries + 1` (the initial attempt plus retries).
A delivery succeeds when the endpoint returns a 2xx HTTP status code. Any non-2xx
response or network error triggers a retry.

## DeliveryStatus

The `DeliveryStatus` enum tracks the state of each delivery attempt:

| Status     | Description                                     |
|------------|-------------------------------------------------|
| `PENDING`  | Delivery has been created but not yet attempted  |
| `SUCCESS`  | Endpoint returned a 2xx status code              |
| `FAILED`   | All retry attempts exhausted without success     |
| `RETRYING` | Currently retrying after a failed attempt        |

## WebhookDelivery

Each delivery is tracked by a `WebhookDelivery` model:

```python
delivery = deliveries[0]
print(delivery.delivery_id)      # UUID string
print(delivery.webhook_name)     # "my-hook"
print(delivery.event_type)       # "agent.completed"
print(delivery.status)           # DeliveryStatus.SUCCESS
print(delivery.attempts)         # 1
print(delivery.max_attempts)     # 4 (1 initial + 3 retries)
print(delivery.response_status)  # 200
print(delivery.error)            # None (or error message on failure)
print(delivery.created_at)       # datetime (UTC)
print(delivery.last_attempt_at)  # datetime (UTC)
```

| Field             | Type              | Description                                   |
|-------------------|-------------------|-----------------------------------------------|
| `delivery_id`     | `str`             | Unique UUID for this delivery                  |
| `webhook_name`    | `str`             | Name of the webhook this delivery belongs to   |
| `event_type`      | `str`             | The event type that triggered this delivery    |
| `status`          | `DeliveryStatus`  | Current delivery status                        |
| `attempts`        | `int`             | Number of delivery attempts made               |
| `max_attempts`    | `int`             | Maximum number of attempts allowed             |
| `response_status` | `int \| None`     | HTTP status code from the last attempt          |
| `error`           | `str \| None`     | Error message from the last failed attempt      |
| `created_at`      | `datetime`        | When the delivery was created (UTC)            |
| `last_attempt_at` | `datetime \| None`| When the last attempt was made (UTC)           |

## Verifying Signatures

On the receiving end, verify the HMAC-SHA256 signature to ensure the payload
authenticity:

```python
import hashlib
import hmac

def verify_webhook(payload_bytes: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

# In your webhook handler (e.g. Flask/FastAPI):
# signature = request.headers["X-Webhook-Signature"]
# is_valid = verify_webhook(request.body, signature, "my-secret-key")
```

!!! warning "Always verify signatures"
    If you configure a `secret` on your webhook, always verify the
    `X-Webhook-Signature` header on the receiving end. This ensures the payload
    was not tampered with in transit and originated from your OpenClaw SDK instance.

## Full Example

```python
import asyncio
from openclaw_sdk.webhooks.manager import (
    WebhookManager,
    WebhookConfig,
    DeliveryStatus,
)

async def main():
    manager = WebhookManager()

    # Register webhooks for different event types
    manager.register(WebhookConfig(
        name="all-events",
        url="https://example.com/hooks/all",
        secret="secret-all",
    ))

    manager.register(WebhookConfig(
        name="errors-only",
        url="https://example.com/hooks/errors",
        events=["agent.failed", "agent.error"],
        secret="secret-errors",
        max_retries=5,
    ))

    # Fire events
    deliveries = await manager.fire("agent.completed", {
        "agent_id": "assistant",
        "result": "Done",
    })
    print(f"Delivered to {len(deliveries)} webhook(s)")

    # Check delivery history
    history = manager.get_deliveries(webhook_name="all-events")
    for d in history:
        print(f"  [{d.status}] {d.event_type} -> {d.attempts} attempts")

    # Retry any failures
    retries = await manager.retry_failed("all-events")
    if retries:
        print(f"Retried {len(retries)} failed delivery(ies)")

    # Disable a webhook without removing it
    hook = manager.get("errors-only")
    if hook:
        hook.enabled = False

    # Unregister when no longer needed
    manager.unregister("all-events")

asyncio.run(main())
```
