"""Tests for ApprovalManager — methods raise NotImplementedError.

approvals.list and approvals.resolve do NOT exist on the OpenClaw gateway
(verified 2026-02-21).  Approvals are push-event based.
"""

from __future__ import annotations

import pytest

from openclaw_sdk.approvals.manager import ApprovalManager
from openclaw_sdk.gateway.mock import MockGateway


def _make_manager() -> tuple[MockGateway, ApprovalManager]:
    mock = MockGateway()
    mock._connected = True
    return mock, ApprovalManager(mock)


async def test_list_requests_raises_not_implemented() -> None:
    _, mgr = _make_manager()

    with pytest.raises(NotImplementedError, match="approvals.list does not exist"):
        await mgr.list_requests()


async def test_resolve_raises_not_implemented() -> None:
    _, mgr = _make_manager()

    with pytest.raises(NotImplementedError, match="approvals.resolve does not exist"):
        await mgr.resolve("req-1", "approve")


async def test_resolve_with_note_raises_not_implemented() -> None:
    _, mgr = _make_manager()

    with pytest.raises(NotImplementedError):
        await mgr.resolve("req-2", "deny", note="Too dangerous")
