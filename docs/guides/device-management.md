# Device Management

OpenClaw supports multiple connected devices — CLI sessions, web UIs, mobile
nodes, and remote machines. The `DeviceManager` lets you manage device
authentication tokens and the pairing workflow.

## Quick Start

```python
import asyncio
from openclaw_sdk import OpenClawClient

async def main():
    async with OpenClawClient.connect() as client:
        devices = client.devices

        # List all paired devices
        paired = await devices.list_paired()
        for device in paired.get("paired", []):
            print(f"{device.get('deviceId')} — {device.get('role')}")

asyncio.run(main())
```

## Listing Paired Devices

View all pending and paired devices:

```python
result = await client.devices.list_paired()

# Pending pairing requests
for req in result.get("pending", []):
    print(f"Pending: {req.get('requestId')} from {req.get('deviceId')}")

# Already paired devices
for device in result.get("paired", []):
    print(f"Paired: {device.get('deviceId')} — role: {device.get('role')}")
```

## Pairing Workflow

When a new device wants to connect, it sends a pairing request. You can
approve or reject it:

```python
# Approve a pairing request
await client.devices.approve_pairing("req_abc123")

# Reject a pairing request
await client.devices.reject_pairing("req_def456")
```

## Removing a Device

Unpair a device and revoke its access:

```python
await client.devices.remove_device("device_abc")
```

!!! warning
    Removing a device immediately disconnects it. The device will need to go
    through the pairing flow again to reconnect.

## Token Management

Each device has an authentication token. Rotate tokens periodically for
security, or revoke them to force re-authentication.

### Rotating Tokens

Generate a new token for a device (the old token is invalidated):

```python
result = await client.devices.rotate_token("device_abc", role="operator")
# Returns the new token in the response
```

### Revoking Tokens

Permanently invalidate a device's token:

```python
await client.devices.revoke_token("device_abc", role="operator")
```

## Device Roles

| Role | Description |
|------|-------------|
| `operator` | Full access — can manage agents, config, and other devices |
| `node` | Node-level access — can invoke actions and emit events |

## Full Example

```python
import asyncio
from openclaw_sdk import OpenClawClient

async def main():
    async with OpenClawClient.connect() as client:
        devices = client.devices

        # List all devices
        result = await devices.list_paired()

        pending = result.get("pending", [])
        paired = result.get("paired", [])

        print(f"Paired devices: {len(paired)}")
        print(f"Pending requests: {len(pending)}")

        # Auto-approve any pending requests (example only)
        for req in pending:
            req_id = req.get("requestId")
            print(f"Approving {req_id}...")
            await devices.approve_pairing(req_id)

        # Rotate token for the first paired device
        if paired:
            device_id = paired[0].get("deviceId")
            role = paired[0].get("role", "operator")
            print(f"Rotating token for {device_id}...")
            await devices.rotate_token(device_id, role)

asyncio.run(main())
```

## API Reference

::: openclaw_sdk.devices.manager.DeviceManager
    options:
      show_source: false
