# Usage Analytics

The `OpsManager` provides real-time usage analytics directly from the OpenClaw
gateway — provider quotas, cost breakdowns, and per-session usage data.

!!! note
    This guide covers **gateway-native analytics** via `client.ops`. For local
    SDK-side cost tracking (per-agent, per-model), see [Cost Tracking](cost-tracking.md).

## Quick Start

```python
import asyncio
from openclaw_sdk import OpenClawClient

async def main():
    async with OpenClawClient.connect() as client:
        ops = client.ops

        # Provider usage status (quotas, plans)
        status = await ops.usage_status()
        print(f"Updated: {status.get('updatedAt')}")

        # Cost breakdown (daily + totals)
        cost = await ops.usage_cost()
        print(f"Total cost: ${cost.get('totals', {}).get('totalCost', 0):.2f}")

        # Per-session analytics
        sessions = await ops.sessions_usage()
        print(f"Sessions tracked: {len(sessions.get('sessions', []))}")

asyncio.run(main())
```

## Provider Usage Status

Check provider quotas, rate limits, and plan details:

```python
status = await client.ops.usage_status()
# {
#   'updatedAt': '2026-02-28T...',
#   'providers': [
#     {
#       'provider': 'anthropic',
#       'displayName': 'Anthropic',
#       'windows': [...],
#       'plan': {...}
#     }
#   ]
# }

for provider in status.get("providers", []):
    name = provider.get("displayName")
    plan = provider.get("plan", {})
    print(f"{name}: {plan.get('name', 'unknown')} plan")
```

## Cost Breakdown

Get detailed cost data broken down by day:

```python
cost = await client.ops.usage_cost()
# {
#   'updatedAt': '...',
#   'days': 7,
#   'daily': [
#     {'date': '2026-02-28', 'input': 12345, 'output': 6789, ...}
#   ],
#   'totals': {
#     'totalInput': ...,
#     'totalOutput': ...,
#     'totalCost': ...
#   }
# }

totals = cost.get("totals", {})
print(f"Total input tokens:  {totals.get('totalInput', 0):,}")
print(f"Total output tokens: {totals.get('totalOutput', 0):,}")

for day in cost.get("daily", []):
    print(f"  {day['date']}: {day.get('input', 0):,} in / {day.get('output', 0):,} out")
```

## Per-Session Usage

Track usage by individual session:

```python
sessions = await client.ops.sessions_usage()
# {
#   'updatedAt': '...',
#   'startDate': '2026-02-21',
#   'endDate': '2026-02-28',
#   'sessions': [
#     {
#       'key': 'agent:main:main',
#       'sessionId': '...',
#       'agentId': 'main',
#       'usage': {'inputTokens': ..., 'outputTokens': ...}
#     }
#   ]
# }

for session in sessions.get("sessions", []):
    key = session.get("key", "")
    usage = session.get("usage", {})
    tokens = usage.get("inputTokens", 0) + usage.get("outputTokens", 0)
    print(f"  {key}: {tokens:,} tokens")
```

## Combining with Local Cost Tracking

For comprehensive cost monitoring, combine gateway analytics with the SDK's
local `CostTracker`:

```python
from openclaw_sdk import OpenClawClient
from openclaw_sdk.tracking.cost import CostTracker

async with OpenClawClient.connect() as client:
    # Gateway-side: real-time provider costs
    cost = await client.ops.usage_cost()
    gateway_total = cost.get("totals", {}).get("totalCost", 0)

    # SDK-side: per-execution cost tracking
    tracker = CostTracker()
    agent = client.get_agent("main")
    result = await agent.execute("Hello")
    tracker.record(result)

    print(f"Gateway total: ${gateway_total:.2f}")
    print(f"Local tracker: {tracker.summary()}")
```

## Full Example

```python
import asyncio
from openclaw_sdk import OpenClawClient

async def main():
    async with OpenClawClient.connect() as client:
        ops = client.ops

        # Full usage dashboard
        print("=== Provider Status ===")
        status = await ops.usage_status()
        for p in status.get("providers", []):
            print(f"  {p.get('displayName')}: {p.get('plan', {}).get('name', 'N/A')}")

        print("\n=== Cost Breakdown ===")
        cost = await ops.usage_cost()
        totals = cost.get("totals", {})
        print(f"  Total tokens: {totals.get('totalInput', 0) + totals.get('totalOutput', 0):,}")

        print("\n=== Daily Breakdown ===")
        for day in cost.get("daily", [])[-7:]:
            print(f"  {day['date']}: {day.get('input', 0):,} in / {day.get('output', 0):,} out")

        print("\n=== Top Sessions ===")
        sessions = await ops.sessions_usage()
        sorted_sessions = sorted(
            sessions.get("sessions", []),
            key=lambda s: s.get("usage", {}).get("inputTokens", 0),
            reverse=True,
        )
        for s in sorted_sessions[:5]:
            usage = s.get("usage", {})
            total = usage.get("inputTokens", 0) + usage.get("outputTokens", 0)
            print(f"  {s.get('key')}: {total:,} tokens")

asyncio.run(main())
```

## API Reference

See [`OpsManager`](../api/managers.md) for the full method reference.
