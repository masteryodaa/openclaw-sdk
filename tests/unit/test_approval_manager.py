"""Tests for ApprovalManager -- resolve() calls exec.approval.resolve RPC.

Pending approvals are push-event based (approval.requested), but resolution
uses the ``exec.approval.resolve`` RPC method (verified 2026-02-21).
"""

from __future__ import annotations

from openclaw_sdk.approvals.manager import ApprovalManager
from openclaw_sdk.gateway.mock import MockGateway


def _make_manager() -> tuple[MockGateway, ApprovalManager]:
    mock = MockGateway()
    mock._connected = True
    return mock, ApprovalManager(mock)


async def test_resolve_approve_calls_gateway() -> None:
    mock, mgr = _make_manager()
    mock.register("exec.approval.resolve", {"ok": True})

    result = await mgr.resolve("req_123", "approve")

    assert result == {"ok": True}
    mock.assert_called("exec.approval.resolve")
    mock.assert_called_with(
        "exec.approval.resolve",
        {"id": "req_123", "decision": "approve"},
    )


async def test_resolve_deny_calls_gateway() -> None:
    mock, mgr = _make_manager()
    mock.register("exec.approval.resolve", {"ok": True})

    result = await mgr.resolve("req_456", "deny")

    assert result == {"ok": True}
    mock.assert_called_with(
        "exec.approval.resolve",
        {"id": "req_456", "decision": "deny"},
    )


async def test_resolve_returns_gateway_response() -> None:
    mock, mgr = _make_manager()
    mock.register(
        "exec.approval.resolve",
        {"resolved": True, "requestId": "req_789"},
    )

    result = await mgr.resolve("req_789", "approve")

    assert result["resolved"] is True
    assert result["requestId"] == "req_789"
