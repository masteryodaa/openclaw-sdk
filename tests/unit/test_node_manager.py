"""Tests for NodeManager (node.* + system-presence gateway surface)."""

from __future__ import annotations

from openclaw_sdk.nodes.manager import NodeManager
from openclaw_sdk.gateway.mock import MockGateway


def _make_manager() -> tuple[MockGateway, NodeManager]:
    mock = MockGateway()
    mock._connected = True
    return mock, NodeManager(mock)


async def test_system_presence_calls_gateway() -> None:
    mock, mgr = _make_manager()
    mock.register("system-presence", {"online": True, "uptime": 3600})

    result = await mgr.system_presence()

    mock.assert_called("system-presence")
    assert result["online"] is True
    assert result["uptime"] == 3600


async def test_list_returns_nodes() -> None:
    mock, mgr = _make_manager()
    mock.register(
        "node.list",
        {"nodes": [{"id": "n1", "role": "worker"}, {"id": "n2", "role": "gateway"}]},
    )

    result = await mgr.list()

    mock.assert_called("node.list")
    assert len(result) == 2
    assert result[0]["id"] == "n1"


async def test_list_returns_empty_when_no_nodes() -> None:
    mock, mgr = _make_manager()
    mock.register("node.list", {"nodes": []})

    result = await mgr.list()

    assert result == []


async def test_describe_passes_node_id() -> None:
    mock, mgr = _make_manager()
    mock.register("node.describe", {"id": "n1", "role": "worker", "cpu": "50%"})

    result = await mgr.describe("n1")

    _, params = mock.calls[-1]
    assert params["id"] == "n1"
    assert result["cpu"] == "50%"


async def test_invoke_passes_action_and_payload() -> None:
    mock, mgr = _make_manager()
    mock.register("node.invoke", {"result": "ok"})

    result = await mgr.invoke("n1", "restart", payload={"force": True})

    _, params = mock.calls[-1]
    assert params["id"] == "n1"
    assert params["action"] == "restart"
    assert params["payload"] == {"force": True}
    assert result["result"] == "ok"


async def test_invoke_without_payload() -> None:
    mock, mgr = _make_manager()
    mock.register("node.invoke", {"result": "ok"})

    await mgr.invoke("n1", "ping")

    _, params = mock.calls[-1]
    assert params["id"] == "n1"
    assert params["action"] == "ping"
    assert "payload" not in params
