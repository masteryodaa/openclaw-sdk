"""Operational endpoints — logs, nodes, devices, approvals."""

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


@router.get("/nodes/{node_id}")
async def describe_node(node_id: str):
    """Get details for a specific node."""
    client = await gateway.get_client()
    return await client.nodes.describe(node_id)


# ---- Devices ----

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
