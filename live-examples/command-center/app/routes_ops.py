"""Operational endpoints — logs, nodes, devices, approvals, usage, system."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from . import gateway

router = APIRouter(prefix="/api/ops", tags=["ops"])


# ---- Logs ----


@router.get("/logs")
async def tail_logs():
    """Tail gateway logs."""
    client = await gateway.get_client()
    return await client.ops.logs_tail()


# ---- System status ----


@router.get("/system/status")
async def system_status():
    """Get gateway system status."""
    client = await gateway.get_client()
    return await client.ops.system_status()


@router.get("/system/memory")
async def memory_status():
    """Get memory / embedding health status."""
    client = await gateway.get_client()
    return await client.ops.memory_status()


@router.get("/system/heartbeat")
async def last_heartbeat():
    """Get last heartbeat info."""
    client = await gateway.get_client()
    return await client.ops.last_heartbeat()


@router.post("/system/heartbeats/{enabled}")
async def set_heartbeats(enabled: bool):
    """Enable or disable heartbeats."""
    client = await gateway.get_client()
    return await client.ops.set_heartbeats(enabled)


@router.post("/system/event")
async def system_event(text: str = "sdk-event"):
    """Emit a system event."""
    client = await gateway.get_client()
    return await client.ops.system_event(text)


@router.post("/system/secrets-reload")
async def secrets_reload():
    """Reload secrets from disk."""
    client = await gateway.get_client()
    return await client.ops.secrets_reload()


@router.post("/system/update")
async def update_run():
    """Run a system update check."""
    client = await gateway.get_client()
    return await client.ops.update_run()


# ---- Usage analytics ----


@router.get("/usage/status")
async def usage_status():
    """Get provider usage status (quotas, plans)."""
    client = await gateway.get_client()
    return await client.ops.usage_status()


@router.get("/usage/cost")
async def usage_cost():
    """Get detailed cost breakdown (daily + totals)."""
    client = await gateway.get_client()
    return await client.ops.usage_cost()


@router.get("/usage/sessions")
async def sessions_usage():
    """Get per-session usage analytics."""
    client = await gateway.get_client()
    return await client.ops.sessions_usage()


# ---- Nodes ----


@router.get("/nodes")
async def list_nodes():
    """List all registered nodes."""
    client = await gateway.get_client()
    return {"nodes": await client.nodes.list()}


@router.get("/nodes/presence")
async def system_presence():
    """Get system presence status."""
    client = await gateway.get_client()
    return await client.nodes.system_presence()


@router.get("/nodes/pairs")
async def node_pair_list():
    """List pending and paired nodes."""
    client = await gateway.get_client()
    return await client.nodes.pair_list()


@router.get("/nodes/{node_id}")
async def describe_node(node_id: str):
    """Get details for a specific node."""
    client = await gateway.get_client()
    return await client.nodes.describe(node_id)


class NodeRenameBody(BaseModel):
    display_name: str


@router.patch("/nodes/{node_id}/rename")
async def rename_node(node_id: str, body: NodeRenameBody):
    """Rename a node."""
    client = await gateway.get_client()
    return await client.nodes.rename(node_id, body.display_name)


class PairingBody(BaseModel):
    request_id: str


@router.post("/nodes/pairs/approve")
async def node_pair_approve(body: PairingBody):
    """Approve a node pairing request."""
    client = await gateway.get_client()
    return await client.nodes.pair_approve(body.request_id)


@router.post("/nodes/pairs/reject")
async def node_pair_reject(body: PairingBody):
    """Reject a node pairing request."""
    client = await gateway.get_client()
    return await client.nodes.pair_reject(body.request_id)


# ---- Devices ----


@router.get("/devices")
async def list_devices():
    """List all pending and paired devices."""
    client = await gateway.get_client()
    return await client.devices.list_paired()


class DeviceTokenBody(BaseModel):
    device_id: str
    role: str


@router.post("/devices/rotate-token")
async def rotate_device_token(body: DeviceTokenBody):
    """Rotate a device's auth token."""
    client = await gateway.get_client()
    result = await client.devices.rotate_token(body.device_id, body.role)
    return {"success": True, "result": result}


@router.post("/devices/revoke-token")
async def revoke_device_token(body: DeviceTokenBody):
    """Revoke a device's auth token."""
    client = await gateway.get_client()
    result = await client.devices.revoke_token(body.device_id, body.role)
    return {"success": True, "result": result}


class DevicePairingBody(BaseModel):
    request_id: str


@router.post("/devices/approve")
async def approve_device(body: DevicePairingBody):
    """Approve a device pairing request."""
    client = await gateway.get_client()
    return await client.devices.approve_pairing(body.request_id)


@router.post("/devices/reject")
async def reject_device(body: DevicePairingBody):
    """Reject a device pairing request."""
    client = await gateway.get_client()
    return await client.devices.reject_pairing(body.request_id)


class DeviceRemoveBody(BaseModel):
    device_id: str


@router.post("/devices/remove")
async def remove_device(body: DeviceRemoveBody):
    """Remove a paired device."""
    client = await gateway.get_client()
    return await client.devices.remove_device(body.device_id)


# ---- Approvals ----


class ApprovalBody(BaseModel):
    request_id: str
    decision: str  # "approve" or "deny"


@router.post("/approvals/resolve")
async def resolve_approval(body: ApprovalBody):
    """Approve or deny a pending execution request."""
    client = await gateway.get_client()
    result = await client.approvals.resolve(body.request_id, body.decision)
    return {"success": True, "result": result}
