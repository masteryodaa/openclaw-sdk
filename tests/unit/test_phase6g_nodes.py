"""Phase 6G — Node expansion: 8 new gateway facades + 8 NodeManager methods.

Tests cover:
- All 8 gateway facade methods (correct RPC method names and params)
- All 8 NodeManager methods (rename, invoke_result, emit_event, pair_*)
- Existing methods (system_presence, list, describe, invoke) still work
- Role-restricted methods document the restriction in their docstrings
"""

from __future__ import annotations


from openclaw_sdk.gateway.mock import MockGateway
from openclaw_sdk.nodes.manager import NodeManager


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #


def _make_gateway() -> MockGateway:
    mock = MockGateway()
    mock._connected = True
    return mock


def _make_manager() -> tuple[MockGateway, NodeManager]:
    mock = _make_gateway()
    return mock, NodeManager(mock)


# ================================================================== #
# Gateway facade tests (8 new methods)
# ================================================================== #


class TestGatewayNodeRename:
    async def test_calls_correct_method(self) -> None:
        gw = _make_gateway()
        gw.register("node.rename", {"ok": True})

        result = await gw.node_rename("n1", "My Node")

        gw.assert_called("node.rename")
        assert result["ok"] is True

    async def test_passes_correct_params(self) -> None:
        gw = _make_gateway()
        gw.register("node.rename", {"ok": True})

        await gw.node_rename("n1", "New Name")

        _, params = gw.calls[-1]
        assert params == {"nodeId": "n1", "displayName": "New Name"}


class TestGatewayNodeInvokeResult:
    async def test_calls_correct_method(self) -> None:
        gw = _make_gateway()
        gw.register("node.invoke.result", {"ok": True})

        result = await gw.node_invoke_result(requestId="r1", output="done")

        gw.assert_called("node.invoke.result")
        assert result["ok"] is True

    async def test_passes_kwargs_as_params(self) -> None:
        gw = _make_gateway()
        gw.register("node.invoke.result", {"ok": True})

        await gw.node_invoke_result(requestId="r1", output="done")

        _, params = gw.calls[-1]
        assert params == {"requestId": "r1", "output": "done"}

    async def test_docstring_mentions_role_restriction(self) -> None:
        from openclaw_sdk.gateway.base import Gateway

        doc = Gateway.node_invoke_result.__doc__ or ""
        assert "node" in doc.lower()
        assert "role" in doc.lower()


class TestGatewayNodeEvent:
    async def test_calls_correct_method(self) -> None:
        gw = _make_gateway()
        gw.register("node.event", {"ok": True})

        result = await gw.node_event(eventType="status", data={"cpu": 50})

        gw.assert_called("node.event")
        assert result["ok"] is True

    async def test_passes_kwargs_as_params(self) -> None:
        gw = _make_gateway()
        gw.register("node.event", {"ok": True})

        await gw.node_event(eventType="heartbeat")

        _, params = gw.calls[-1]
        assert params == {"eventType": "heartbeat"}

    async def test_docstring_mentions_role_restriction(self) -> None:
        from openclaw_sdk.gateway.base import Gateway

        doc = Gateway.node_event.__doc__ or ""
        assert "node" in doc.lower()
        assert "role" in doc.lower()


class TestGatewayNodePairRequest:
    async def test_calls_correct_method(self) -> None:
        gw = _make_gateway()
        gw.register("node.pair.request", {"requestId": "pr1"})

        result = await gw.node_pair_request("n1")

        gw.assert_called("node.pair.request")
        assert result["requestId"] == "pr1"

    async def test_passes_correct_params(self) -> None:
        gw = _make_gateway()
        gw.register("node.pair.request", {"requestId": "pr1"})

        await gw.node_pair_request("n1")

        _, params = gw.calls[-1]
        assert params == {"nodeId": "n1"}


class TestGatewayNodePairList:
    async def test_calls_correct_method(self) -> None:
        gw = _make_gateway()
        gw.register("node.pair.list", {"pending": [], "paired": []})

        result = await gw.node_pair_list()

        gw.assert_called("node.pair.list")
        assert result["pending"] == []
        assert result["paired"] == []

    async def test_passes_empty_params(self) -> None:
        gw = _make_gateway()
        gw.register("node.pair.list", {"pending": [], "paired": []})

        await gw.node_pair_list()

        _, params = gw.calls[-1]
        assert params == {}


class TestGatewayNodePairApprove:
    async def test_calls_correct_method(self) -> None:
        gw = _make_gateway()
        gw.register("node.pair.approve", {"ok": True})

        result = await gw.node_pair_approve("pr1")

        gw.assert_called("node.pair.approve")
        assert result["ok"] is True

    async def test_passes_correct_params(self) -> None:
        gw = _make_gateway()
        gw.register("node.pair.approve", {"ok": True})

        await gw.node_pair_approve("pr1")

        _, params = gw.calls[-1]
        assert params == {"requestId": "pr1"}


class TestGatewayNodePairReject:
    async def test_calls_correct_method(self) -> None:
        gw = _make_gateway()
        gw.register("node.pair.reject", {"ok": True})

        result = await gw.node_pair_reject("pr1")

        gw.assert_called("node.pair.reject")
        assert result["ok"] is True

    async def test_passes_correct_params(self) -> None:
        gw = _make_gateway()
        gw.register("node.pair.reject", {"ok": True})

        await gw.node_pair_reject("pr1")

        _, params = gw.calls[-1]
        assert params == {"requestId": "pr1"}


class TestGatewayNodePairVerify:
    async def test_calls_correct_method(self) -> None:
        gw = _make_gateway()
        gw.register("node.pair.verify", {"verified": True})

        result = await gw.node_pair_verify("n1", "tok123")

        gw.assert_called("node.pair.verify")
        assert result["verified"] is True

    async def test_passes_correct_params(self) -> None:
        gw = _make_gateway()
        gw.register("node.pair.verify", {"verified": True})

        await gw.node_pair_verify("n1", "tok123")

        _, params = gw.calls[-1]
        assert params == {"nodeId": "n1", "token": "tok123"}


# ================================================================== #
# NodeManager tests — existing methods still work
# ================================================================== #


class TestNodeManagerExistingMethods:
    """Verify the 4 pre-existing methods are unaffected."""

    async def test_system_presence(self) -> None:
        mock, mgr = _make_manager()
        mock.register("system-presence", {"online": True})

        result = await mgr.system_presence()

        mock.assert_called("system-presence")
        assert result["online"] is True

    async def test_list(self) -> None:
        mock, mgr = _make_manager()
        mock.register("node.list", {"nodes": [{"id": "n1"}]})

        result = await mgr.list()

        mock.assert_called("node.list")
        assert len(result) == 1

    async def test_describe(self) -> None:
        mock, mgr = _make_manager()
        mock.register("node.describe", {"id": "n1", "role": "worker"})

        result = await mgr.describe("n1")

        _, params = mock.calls[-1]
        assert params["id"] == "n1"
        assert result["role"] == "worker"

    async def test_invoke(self) -> None:
        mock, mgr = _make_manager()
        mock.register("node.invoke", {"result": "ok"})

        result = await mgr.invoke("n1", "restart", payload={"force": True})

        _, params = mock.calls[-1]
        assert params["id"] == "n1"
        assert params["action"] == "restart"
        assert params["payload"] == {"force": True}
        assert result["result"] == "ok"


# ================================================================== #
# NodeManager tests — 8 new methods
# ================================================================== #


class TestNodeManagerRename:
    async def test_calls_correct_method(self) -> None:
        mock, mgr = _make_manager()
        mock.register("node.rename", {"ok": True})

        result = await mgr.rename("n1", "My Node")

        mock.assert_called("node.rename")
        assert result["ok"] is True

    async def test_passes_correct_params(self) -> None:
        mock, mgr = _make_manager()
        mock.register("node.rename", {"ok": True})

        await mgr.rename("n1", "New Name")

        _, params = mock.calls[-1]
        assert params == {"nodeId": "n1", "displayName": "New Name"}


class TestNodeManagerInvokeResult:
    async def test_calls_correct_method(self) -> None:
        mock, mgr = _make_manager()
        mock.register("node.invoke.result", {"ok": True})

        result = await mgr.invoke_result(requestId="r1", output="done")

        mock.assert_called("node.invoke.result")
        assert result["ok"] is True

    async def test_passes_kwargs_as_params(self) -> None:
        mock, mgr = _make_manager()
        mock.register("node.invoke.result", {"ok": True})

        await mgr.invoke_result(requestId="r1", output="hello")

        _, params = mock.calls[-1]
        assert params == {"requestId": "r1", "output": "hello"}

    async def test_docstring_notes_role_restriction(self) -> None:
        doc = NodeManager.invoke_result.__doc__ or ""
        assert "node" in doc.lower()
        assert "role" in doc.lower()


class TestNodeManagerEmitEvent:
    async def test_calls_correct_method(self) -> None:
        mock, mgr = _make_manager()
        mock.register("node.event", {"ok": True})

        result = await mgr.emit_event(eventType="status", data={"cpu": 50})

        mock.assert_called("node.event")
        assert result["ok"] is True

    async def test_passes_kwargs_as_params(self) -> None:
        mock, mgr = _make_manager()
        mock.register("node.event", {"ok": True})

        await mgr.emit_event(eventType="heartbeat")

        _, params = mock.calls[-1]
        assert params == {"eventType": "heartbeat"}

    async def test_docstring_notes_role_restriction(self) -> None:
        doc = NodeManager.emit_event.__doc__ or ""
        assert "node" in doc.lower()
        assert "role" in doc.lower()


class TestNodeManagerPairRequest:
    async def test_calls_correct_method(self) -> None:
        mock, mgr = _make_manager()
        mock.register("node.pair.request", {"requestId": "pr1"})

        result = await mgr.pair_request("n1")

        mock.assert_called("node.pair.request")
        assert result["requestId"] == "pr1"

    async def test_passes_correct_params(self) -> None:
        mock, mgr = _make_manager()
        mock.register("node.pair.request", {"requestId": "pr1"})

        await mgr.pair_request("n1")

        _, params = mock.calls[-1]
        assert params == {"nodeId": "n1"}


class TestNodeManagerPairList:
    async def test_calls_correct_method(self) -> None:
        mock, mgr = _make_manager()
        mock.register("node.pair.list", {"pending": ["p1"], "paired": ["n1"]})

        result = await mgr.pair_list()

        mock.assert_called("node.pair.list")
        assert result["pending"] == ["p1"]
        assert result["paired"] == ["n1"]

    async def test_passes_empty_params(self) -> None:
        mock, mgr = _make_manager()
        mock.register("node.pair.list", {"pending": [], "paired": []})

        await mgr.pair_list()

        _, params = mock.calls[-1]
        assert params == {}


class TestNodeManagerPairApprove:
    async def test_calls_correct_method(self) -> None:
        mock, mgr = _make_manager()
        mock.register("node.pair.approve", {"ok": True})

        result = await mgr.pair_approve("pr1")

        mock.assert_called("node.pair.approve")
        assert result["ok"] is True

    async def test_passes_correct_params(self) -> None:
        mock, mgr = _make_manager()
        mock.register("node.pair.approve", {"ok": True})

        await mgr.pair_approve("pr1")

        _, params = mock.calls[-1]
        assert params == {"requestId": "pr1"}


class TestNodeManagerPairReject:
    async def test_calls_correct_method(self) -> None:
        mock, mgr = _make_manager()
        mock.register("node.pair.reject", {"ok": True})

        result = await mgr.pair_reject("pr1")

        mock.assert_called("node.pair.reject")
        assert result["ok"] is True

    async def test_passes_correct_params(self) -> None:
        mock, mgr = _make_manager()
        mock.register("node.pair.reject", {"ok": True})

        await mgr.pair_reject("pr1")

        _, params = mock.calls[-1]
        assert params == {"requestId": "pr1"}


class TestNodeManagerPairVerify:
    async def test_calls_correct_method(self) -> None:
        mock, mgr = _make_manager()
        mock.register("node.pair.verify", {"verified": True})

        result = await mgr.pair_verify("n1", "tok123")

        mock.assert_called("node.pair.verify")
        assert result["verified"] is True

    async def test_passes_correct_params(self) -> None:
        mock, mgr = _make_manager()
        mock.register("node.pair.verify", {"verified": True})

        await mgr.pair_verify("n1", "tok123")

        _, params = mock.calls[-1]
        assert params == {"nodeId": "n1", "token": "tok123"}
