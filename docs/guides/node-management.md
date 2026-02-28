# Node Management

In a multi-node OpenClaw deployment, each process registers itself with the
gateway. The `NodeManager` lets you discover nodes, monitor presence, invoke
actions on remote nodes, and manage node pairing.

## Quick Start

```python
import asyncio
from openclaw_sdk import OpenClawClient

async def main():
    async with OpenClawClient.connect() as client:
        nodes = client.nodes

        # Check system presence
        presence = await nodes.system_presence()
        print(f"Online nodes: {presence}")

        # List all registered nodes
        node_list = await nodes.list()
        for node in node_list:
            print(f"{node.get('id')} — {node.get('displayName', 'unnamed')}")

asyncio.run(main())
```

## System Presence

Get a high-level overview of the node network:

```python
presence = await client.nodes.system_presence()
# Returns presence info: online nodes, uptime, etc.
```

## Listing Nodes

```python
nodes = await client.nodes.list()
for node in nodes:
    print(f"  {node.get('id')}: {node.get('displayName')}")
```

## Node Details

Get detailed information about a specific node:

```python
info = await client.nodes.describe("node-abc")
print(f"Node: {info.get('displayName')}")
print(f"Role: {info.get('role')}")
print(f"Status: {info.get('status')}")
```

## Renaming a Node

```python
await client.nodes.rename("node-abc", "Production Server")
```

## Invoking Actions

Send an action to a specific node:

```python
result = await client.nodes.invoke(
    node_id="node-abc",
    action="health-check",
    payload={"verbose": True},
)
print(f"Result: {result}")
```

## Node Pairing

New nodes must be paired with the gateway before they can participate.

### Pairing Workflow

```
1. Node sends pair request  →  node.pair.request
2. Operator lists pending   →  node.pair.list
3. Operator approves        →  node.pair.approve
4. Node verifies pairing    →  node.pair.verify
```

### Listing Pairing Status

```python
pairs = await client.nodes.pair_list()

for pending in pairs.get("pending", []):
    print(f"Pending: {pending.get('requestId')} from {pending.get('nodeId')}")

for paired in pairs.get("paired", []):
    print(f"Paired: {paired.get('nodeId')}")
```

### Approving and Rejecting

```python
# Approve a pairing request
await client.nodes.pair_approve("req_abc123")

# Reject a pairing request
await client.nodes.pair_reject("req_def456")
```

### Requesting and Verifying

These are typically called from the node side:

```python
# Request pairing (from the node)
await client.nodes.pair_request("my-node-id")

# Verify pairing with a token (from the node)
await client.nodes.pair_verify("my-node-id", token="verification-token")
```

## Role-Restricted Methods

Two methods require the `node` role and are intended for node-side code:

| Method | Gateway RPC | Description |
|--------|-------------|-------------|
| `invoke_result()` | `node.invoke.result` | Submit an invoke result back |
| `emit_event()` | `node.event` | Emit a node event |

These will raise a `GatewayError` if called from an `operator`-role session.

## Full Example

```python
import asyncio
from openclaw_sdk import OpenClawClient

async def main():
    async with OpenClawClient.connect() as client:
        nodes = client.nodes

        # Monitor the network
        presence = await nodes.system_presence()
        print(f"System presence: {presence}")

        # List and describe nodes
        node_list = await nodes.list()
        print(f"Registered nodes: {len(node_list)}")

        for node in node_list:
            node_id = node.get("id", "")
            print(f"  {node_id}: {node.get('displayName', 'unnamed')}")

        # Check pairing status
        pairs = await nodes.pair_list()
        pending = pairs.get("pending", [])
        if pending:
            print(f"{len(pending)} pending pairing requests")

asyncio.run(main())
```

## API Reference

See the full [NodeManager API reference](../api/managers.md#openclaw_sdk.nodes.manager.NodeManager).
