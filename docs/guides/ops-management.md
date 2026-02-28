# Ops Management

The `OpsManager` provides system-level operational commands for monitoring and
managing your OpenClaw gateway — log access, heartbeat control, system status,
memory health, secret management, and updates.

## Quick Start

```python
import asyncio
from openclaw_sdk import OpenClawClient

async def main():
    async with OpenClawClient.connect() as client:
        ops = client.ops

        # System status overview
        status = await ops.system_status()
        print(f"Heartbeat: {status.get('heartbeat')}")
        print(f"Sessions: {status.get('sessions')}")

        # Tail recent logs
        logs = await ops.logs_tail()
        for line in logs.get("lines", [])[-5:]:
            print(line)

asyncio.run(main())
```

## System Status

Get a snapshot of the gateway's current state:

```python
status = await client.ops.system_status()
# {
#   'linkChannel': ...,
#   'heartbeat': {...},
#   'channelSummary': {...},
#   'queuedSystemEvents': 0,
#   'sessions': {...}
# }
```

## Memory Health

Check the embedding/memory subsystem:

```python
memory = await client.ops.memory_status()
# {
#   'agentId': 'main',
#   'provider': 'openai',
#   'embedding': {'ok': True}
# }

if memory.get("embedding", {}).get("ok"):
    print("Memory subsystem healthy")
else:
    print(f"Memory issue: {memory.get('embedding', {}).get('error')}")
```

## Log Tailing

Fetch the most recent log entries:

```python
logs = await client.ops.logs_tail()

print(f"Log file: {logs.get('file')}")
print(f"Size: {logs.get('size')} bytes")

for line in logs.get("lines", []):
    print(line)
```

## Heartbeat Management

Control and monitor the gateway's heartbeat system:

```python
# Check last heartbeat
hb = await client.ops.last_heartbeat()
print(f"Last heartbeat: {hb.get('ts')}")
print(f"Status: {hb.get('status')}")
print(f"Duration: {hb.get('durationMs')}ms")

# Enable heartbeats
await client.ops.set_heartbeats(True)

# Disable heartbeats
await client.ops.set_heartbeats(False)
```

## System Events

Emit custom system events for logging and monitoring:

```python
await client.ops.system_event("SDK health check completed")
await client.ops.system_event("Deployment started: v2.1.0")
```

## Secret Management

Reload secrets from disk without restarting the gateway:

```python
result = await client.ops.secrets_reload()
print(f"Reloaded: {result.get('ok')}")
print(f"Warnings: {result.get('warningCount', 0)}")
```

## System Updates

Check for and run gateway updates:

```python
result = await client.ops.update_run()
# {
#   'ok': True,
#   'result': {'status': 'up-to-date', 'mode': '...'},
#   'restart': False,
#   'sentinel': '...'
# }

update_status = result.get("result", {}).get("status")
print(f"Update status: {update_status}")

if result.get("restart"):
    print("Gateway restart required")
```

## Legacy Usage Summary

For backward compatibility, `usage_summary()` aggregates token usage from
session metadata:

```python
summary = await client.ops.usage_summary()
print(f"Total tokens: {summary['totalTokens']:,}")
print(f"Sessions: {summary['sessionCount']}")
```

!!! tip
    Prefer `usage_status()` and `usage_cost()` for real-time provider-level
    analytics. Use `usage_summary()` only if you need a quick aggregate from
    session metadata.

## Full Example

```python
import asyncio
from openclaw_sdk import OpenClawClient

async def main():
    async with OpenClawClient.connect() as client:
        ops = client.ops

        # System health dashboard
        print("=== System Status ===")
        status = await ops.system_status()
        print(f"  Sessions: {status.get('sessions')}")

        print("\n=== Memory Health ===")
        memory = await ops.memory_status()
        embedding = memory.get("embedding", {})
        print(f"  Provider: {memory.get('provider')}")
        print(f"  Healthy: {embedding.get('ok')}")

        print("\n=== Heartbeat ===")
        hb = await ops.last_heartbeat()
        print(f"  Last: {hb.get('ts')}")
        print(f"  Status: {hb.get('status')}")

        print("\n=== Recent Logs ===")
        logs = await ops.logs_tail()
        for line in logs.get("lines", [])[-3:]:
            print(f"  {line}")

        print("\n=== Secrets ===")
        secrets = await ops.secrets_reload()
        print(f"  OK: {secrets.get('ok')}")
        print(f"  Warnings: {secrets.get('warningCount', 0)}")

        # Emit a test event
        await ops.system_event("ops-dashboard-check")
        print("\nSystem event emitted.")

asyncio.run(main())
```

## API Reference

::: openclaw_sdk.ops.manager.OpsManager
    options:
      show_source: false
