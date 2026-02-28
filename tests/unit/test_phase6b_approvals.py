"""Tests for Phase 6B: Exec Approvals System (6 new gateway methods).

Covers:
- 6 new gateway facade methods on Gateway ABC
- 6 new ApprovalManager methods
- Optional parameter omission (None values not sent)
- Optimistic concurrency (baseHash passed when provided)
"""

from __future__ import annotations

from openclaw_sdk.approvals.manager import ApprovalManager
from openclaw_sdk.gateway.mock import MockGateway

# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #


def _make_gateway() -> MockGateway:
    mock = MockGateway()
    mock._connected = True
    return mock


def _make_manager() -> tuple[MockGateway, ApprovalManager]:
    mock = _make_gateway()
    return mock, ApprovalManager(mock)


# ================================================================== #
# 1. Gateway facade: exec.approval.request
# ================================================================== #


async def test_exec_approval_request_minimal() -> None:
    gw = _make_gateway()
    gw.register(
        "exec.approval.request",
        {"id": "apr-1", "decision": "allow-once", "createdAtMs": 1000, "expiresAtMs": 2000},
    )

    result = await gw.exec_approval_request("rm -rf /tmp/foo")

    method, params = gw.calls[-1]
    assert method == "exec.approval.request"
    assert params == {"command": "rm -rf /tmp/foo"}
    assert result["id"] == "apr-1"
    assert result["decision"] == "allow-once"


async def test_exec_approval_request_all_optional_params() -> None:
    gw = _make_gateway()
    gw.register("exec.approval.request", {"id": "apr-2", "decision": "deny"})

    await gw.exec_approval_request(
        "docker build .",
        timeout_ms=30000,
        agent_id="bot-a",
        session_key="agent:bot-a:main",
        node_id="node-1",
    )

    _, params = gw.calls[-1]
    assert params == {
        "command": "docker build .",
        "timeoutMs": 30000,
        "agentId": "bot-a",
        "sessionKey": "agent:bot-a:main",
        "nodeId": "node-1",
    }


async def test_exec_approval_request_omits_none_params() -> None:
    gw = _make_gateway()
    gw.register("exec.approval.request", {"id": "apr-3", "decision": None})

    await gw.exec_approval_request("ls", timeout_ms=None, agent_id=None)

    _, params = gw.calls[-1]
    assert params == {"command": "ls"}
    assert "timeoutMs" not in params
    assert "agentId" not in params
    assert "sessionKey" not in params
    assert "nodeId" not in params


# ================================================================== #
# 2. Gateway facade: exec.approval.waitDecision
# ================================================================== #


async def test_exec_approval_wait_decision() -> None:
    gw = _make_gateway()
    gw.register(
        "exec.approval.waitDecision",
        {"id": "apr-1", "decision": "allow-always", "createdAtMs": 1000, "expiresAtMs": 5000},
    )

    result = await gw.exec_approval_wait_decision("apr-1")

    method, params = gw.calls[-1]
    assert method == "exec.approval.waitDecision"
    assert params == {"id": "apr-1"}
    assert result["decision"] == "allow-always"


# ================================================================== #
# 3. Gateway facade: exec.approvals.get
# ================================================================== #


async def test_exec_approvals_get() -> None:
    gw = _make_gateway()
    gw.register(
        "exec.approvals.get",
        {
            "path": "/home/.openclaw/approvals.json",
            "exists": True,
            "hash": "abc123",
            "file": {"version": 1, "socket": "/tmp/oc.sock", "defaults": {}, "agents": {}},
        },
    )

    result = await gw.exec_approvals_get()

    method, params = gw.calls[-1]
    assert method == "exec.approvals.get"
    assert params == {}
    assert result["exists"] is True
    assert result["hash"] == "abc123"
    assert result["file"]["version"] == 1


# ================================================================== #
# 4. Gateway facade: exec.approvals.set
# ================================================================== #


async def test_exec_approvals_set_without_hash() -> None:
    gw = _make_gateway()
    gw.register("exec.approvals.set", {"path": "/approvals.json", "exists": True, "hash": "new1"})

    file_data = {"version": 1, "defaults": {"mode": "confirm"}}
    result = await gw.exec_approvals_set(file_data)

    _, params = gw.calls[-1]
    assert params == {"file": {"version": 1, "defaults": {"mode": "confirm"}}}
    assert "baseHash" not in params
    assert result["hash"] == "new1"


async def test_exec_approvals_set_with_hash() -> None:
    gw = _make_gateway()
    gw.register("exec.approvals.set", {"hash": "new2"})

    file_data = {"version": 2, "agents": {}}
    await gw.exec_approvals_set(file_data, base_hash="old-hash")

    _, params = gw.calls[-1]
    assert params == {
        "file": {"version": 2, "agents": {}},
        "baseHash": "old-hash",
    }


# ================================================================== #
# 5. Gateway facade: exec.approvals.node.get
# ================================================================== #


async def test_exec_approvals_node_get() -> None:
    gw = _make_gateway()
    gw.register(
        "exec.approvals.node.get",
        {"file": {"version": 1, "defaults": {"mode": "auto"}}, "hash": "node-h1"},
    )

    result = await gw.exec_approvals_node_get("node-42")

    method, params = gw.calls[-1]
    assert method == "exec.approvals.node.get"
    assert params == {"nodeId": "node-42"}
    assert result["file"]["version"] == 1


# ================================================================== #
# 6. Gateway facade: exec.approvals.node.set
# ================================================================== #


async def test_exec_approvals_node_set_without_hash() -> None:
    gw = _make_gateway()
    gw.register("exec.approvals.node.set", {"hash": "nh1"})

    file_data = {"version": 1, "defaults": {}}
    await gw.exec_approvals_node_set("node-42", file_data)

    _, params = gw.calls[-1]
    assert params == {"nodeId": "node-42", "file": {"version": 1, "defaults": {}}}
    assert "baseHash" not in params


async def test_exec_approvals_node_set_with_hash() -> None:
    gw = _make_gateway()
    gw.register("exec.approvals.node.set", {"hash": "nh2"})

    file_data = {"version": 2, "agents": {"bot-a": {"mode": "deny"}}}
    await gw.exec_approvals_node_set("node-42", file_data, base_hash="old-node-hash")

    _, params = gw.calls[-1]
    assert params == {
        "nodeId": "node-42",
        "file": {"version": 2, "agents": {"bot-a": {"mode": "deny"}}},
        "baseHash": "old-node-hash",
    }


# ================================================================== #
# 7. ApprovalManager.request
# ================================================================== #


async def test_manager_request_minimal() -> None:
    mock, mgr = _make_manager()
    mock.register(
        "exec.approval.request",
        {"id": "apr-m1", "decision": "allow-once", "createdAtMs": 100, "expiresAtMs": 200},
    )

    result = await mgr.request("npm install")

    mock.assert_called("exec.approval.request")
    mock.assert_called_with("exec.approval.request", {"command": "npm install"})
    assert result["id"] == "apr-m1"
    assert result["decision"] == "allow-once"


async def test_manager_request_all_params() -> None:
    mock, mgr = _make_manager()
    mock.register("exec.approval.request", {"id": "apr-m2", "decision": "deny"})

    await mgr.request(
        "pip install torch",
        timeout_ms=60000,
        agent_id="ml-bot",
        session_key="agent:ml-bot:train",
        node_id="gpu-node",
    )

    mock.assert_called_with(
        "exec.approval.request",
        {
            "command": "pip install torch",
            "timeoutMs": 60000,
            "agentId": "ml-bot",
            "sessionKey": "agent:ml-bot:train",
            "nodeId": "gpu-node",
        },
    )


async def test_manager_request_omits_none() -> None:
    mock, mgr = _make_manager()
    mock.register("exec.approval.request", {"id": "apr-m3"})

    await mgr.request("echo hi", timeout_ms=None, node_id=None)

    _, params = mock.calls[-1]
    assert params == {"command": "echo hi"}
    assert "timeoutMs" not in params
    assert "nodeId" not in params


# ================================================================== #
# 8. ApprovalManager.wait_decision
# ================================================================== #


async def test_manager_wait_decision() -> None:
    mock, mgr = _make_manager()
    mock.register(
        "exec.approval.waitDecision",
        {"id": "apr-w1", "decision": "allow-always", "createdAtMs": 50, "expiresAtMs": 150},
    )

    result = await mgr.wait_decision("apr-w1")

    mock.assert_called("exec.approval.waitDecision")
    mock.assert_called_with("exec.approval.waitDecision", {"id": "apr-w1"})
    assert result["decision"] == "allow-always"


# ================================================================== #
# 9. ApprovalManager.get_settings
# ================================================================== #


async def test_manager_get_settings() -> None:
    mock, mgr = _make_manager()
    mock.register(
        "exec.approvals.get",
        {
            "path": "/config/approvals.json",
            "exists": True,
            "hash": "h1",
            "file": {"version": 1, "socket": "/tmp/s.sock"},
        },
    )

    result = await mgr.get_settings()

    mock.assert_called("exec.approvals.get")
    mock.assert_called_with("exec.approvals.get", {})
    assert result["exists"] is True
    assert result["file"]["version"] == 1


# ================================================================== #
# 10. ApprovalManager.set_settings
# ================================================================== #


async def test_manager_set_settings_without_hash() -> None:
    mock, mgr = _make_manager()
    mock.register("exec.approvals.set", {"hash": "new-h"})

    file_data = {"version": 1, "defaults": {"mode": "auto"}}
    result = await mgr.set_settings(file_data)

    mock.assert_called_with("exec.approvals.set", {"file": file_data})
    assert result["hash"] == "new-h"


async def test_manager_set_settings_with_hash() -> None:
    mock, mgr = _make_manager()
    mock.register("exec.approvals.set", {"hash": "updated-h"})

    file_data = {"version": 2, "agents": {"bot-a": {}}}
    await mgr.set_settings(file_data, base_hash="prev-hash")

    mock.assert_called_with(
        "exec.approvals.set",
        {"file": file_data, "baseHash": "prev-hash"},
    )


async def test_manager_set_settings_omits_none_hash() -> None:
    mock, mgr = _make_manager()
    mock.register("exec.approvals.set", {"hash": "x"})

    await mgr.set_settings({"version": 1}, base_hash=None)

    _, params = mock.calls[-1]
    assert "baseHash" not in params


# ================================================================== #
# 11. ApprovalManager.get_node_settings
# ================================================================== #


async def test_manager_get_node_settings() -> None:
    mock, mgr = _make_manager()
    mock.register(
        "exec.approvals.node.get",
        {"file": {"version": 1}, "hash": "node-h1"},
    )

    result = await mgr.get_node_settings("node-99")

    mock.assert_called("exec.approvals.node.get")
    mock.assert_called_with("exec.approvals.node.get", {"nodeId": "node-99"})
    assert result["hash"] == "node-h1"


# ================================================================== #
# 12. ApprovalManager.set_node_settings
# ================================================================== #


async def test_manager_set_node_settings_without_hash() -> None:
    mock, mgr = _make_manager()
    mock.register("exec.approvals.node.set", {"hash": "nh-new"})

    file_data = {"version": 1, "defaults": {"mode": "confirm"}}
    await mgr.set_node_settings("node-99", file_data)

    mock.assert_called_with(
        "exec.approvals.node.set",
        {"nodeId": "node-99", "file": file_data},
    )


async def test_manager_set_node_settings_with_hash() -> None:
    mock, mgr = _make_manager()
    mock.register("exec.approvals.node.set", {"hash": "nh-upd"})

    file_data = {"version": 2, "agents": {}}
    await mgr.set_node_settings("node-99", file_data, base_hash="old-nh")

    mock.assert_called_with(
        "exec.approvals.node.set",
        {"nodeId": "node-99", "file": file_data, "baseHash": "old-nh"},
    )


async def test_manager_set_node_settings_omits_none_hash() -> None:
    mock, mgr = _make_manager()
    mock.register("exec.approvals.node.set", {"hash": "nh-x"})

    await mgr.set_node_settings("node-99", {"version": 1}, base_hash=None)

    _, params = mock.calls[-1]
    assert "baseHash" not in params


# ================================================================== #
# 13. Edge cases
# ================================================================== #


async def test_approval_request_expired_decision_is_null() -> None:
    """Expired approvals return decision=null."""
    gw = _make_gateway()
    gw.register(
        "exec.approval.request",
        {"id": "apr-exp", "decision": None, "createdAtMs": 100, "expiresAtMs": 100},
    )

    result = await gw.exec_approval_request("sleep 100", timeout_ms=1)

    assert result["decision"] is None


async def test_approval_request_partial_optional_params() -> None:
    """Only provided optional params are sent."""
    gw = _make_gateway()
    gw.register("exec.approval.request", {"id": "apr-p"})

    await gw.exec_approval_request("whoami", agent_id="bot-x")

    _, params = gw.calls[-1]
    assert params == {"command": "whoami", "agentId": "bot-x"}
    assert "timeoutMs" not in params
    assert "sessionKey" not in params
    assert "nodeId" not in params


async def test_existing_resolve_still_works() -> None:
    """The existing resolve() method is unchanged."""
    mock, mgr = _make_manager()
    mock.register("exec.approval.resolve", {"ok": True})

    result = await mgr.resolve("req-existing", "approve")

    mock.assert_called_with(
        "exec.approval.resolve",
        {"id": "req-existing", "decision": "approve"},
    )
    assert result["ok"] is True
