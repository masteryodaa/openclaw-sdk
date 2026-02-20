"""Tests for Gateway base class facade methods (chat, sessions, config, approvals, nodes, ops)."""

from __future__ import annotations

from openclaw_sdk.gateway.mock import MockGateway


def _make_gateway() -> MockGateway:
    mock = MockGateway()
    mock._connected = True
    return mock


# ------------------------------------------------------------------ #
# Chat facade
# ------------------------------------------------------------------ #


async def test_chat_history_returns_messages() -> None:
    gw = _make_gateway()
    gw.register(
        "chat.history",
        {"messages": [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]},
    )

    result = await gw.chat_history("agent:bot:main")

    _, params = gw.calls[-1]
    assert params["sessionKey"] == "agent:bot:main"
    assert params["limit"] == 100
    assert len(result) == 2


async def test_chat_history_custom_limit() -> None:
    gw = _make_gateway()
    gw.register("chat.history", {"messages": []})

    await gw.chat_history("agent:bot:main", limit=10)

    _, params = gw.calls[-1]
    assert params["limit"] == 10


async def test_chat_abort_sends_session_key() -> None:
    gw = _make_gateway()
    gw.register("chat.abort", {})

    result = await gw.chat_abort("agent:bot:main")

    _, params = gw.calls[-1]
    assert params["sessionKey"] == "agent:bot:main"
    assert isinstance(result, dict)


async def test_chat_inject_sends_message() -> None:
    gw = _make_gateway()
    gw.register("chat.inject", {"ok": True})

    result = await gw.chat_inject("agent:bot:main", "You are helpful")

    _, params = gw.calls[-1]
    assert params["sessionKey"] == "agent:bot:main"
    assert params["message"] == "You are helpful"
    assert result["ok"] is True


# ------------------------------------------------------------------ #
# Sessions facade
# ------------------------------------------------------------------ #


async def test_sessions_list() -> None:
    gw = _make_gateway()
    gw.register("sessions.list", {"sessions": [{"key": "agent:a:main"}]})

    result = await gw.sessions_list()

    assert len(result) == 1


async def test_sessions_preview_takes_key_list() -> None:
    gw = _make_gateway()
    gw.register("sessions.preview", {"tokens": 500})

    result = await gw.sessions_preview(["agent:a:main", "agent:b:main"])

    _, params = gw.calls[-1]
    assert params["keys"] == ["agent:a:main", "agent:b:main"]
    assert result["tokens"] == 500


async def test_sessions_resolve_uses_key() -> None:
    gw = _make_gateway()
    gw.register("sessions.resolve", {"status": "idle"})

    result = await gw.sessions_resolve("agent:a:main")

    _, params = gw.calls[-1]
    assert params["key"] == "agent:a:main"
    assert result["status"] == "idle"


async def test_sessions_patch_uses_key_and_spreads_patch() -> None:
    gw = _make_gateway()
    gw.register("sessions.patch", {"ok": True})

    result = await gw.sessions_patch("agent:a:main", {"systemPrompt": "new"})

    _, params = gw.calls[-1]
    assert params["key"] == "agent:a:main"
    assert params["systemPrompt"] == "new"
    assert result["ok"] is True


async def test_sessions_reset_uses_key() -> None:
    gw = _make_gateway()
    gw.register("sessions.reset", {})

    result = await gw.sessions_reset("agent:a:main")

    _, params = gw.calls[-1]
    assert params["key"] == "agent:a:main"
    assert isinstance(result, dict)


async def test_sessions_delete_uses_key() -> None:
    gw = _make_gateway()
    gw.register("sessions.delete", {})

    result = await gw.sessions_delete("agent:a:main")

    _, params = gw.calls[-1]
    assert params["key"] == "agent:a:main"
    assert isinstance(result, dict)


async def test_sessions_compact_uses_key() -> None:
    gw = _make_gateway()
    gw.register("sessions.compact", {"newTokens": 200})

    result = await gw.sessions_compact("agent:a:main")

    _, params = gw.calls[-1]
    assert params["key"] == "agent:a:main"
    assert result["newTokens"] == 200


# ------------------------------------------------------------------ #
# Config facade
# ------------------------------------------------------------------ #


async def test_config_get() -> None:
    gw = _make_gateway()
    gw.register("config.get", {"raw": '{"logLevel":"INFO"}', "parsed": {}})

    result = await gw.config_get()

    assert result["raw"] == '{"logLevel":"INFO"}'


async def test_config_schema() -> None:
    gw = _make_gateway()
    gw.register("config.schema", {"schema": {"type": "object"}})

    result = await gw.config_schema()

    assert result["schema"]["type"] == "object"


async def test_config_set_sends_raw() -> None:
    gw = _make_gateway()
    gw.register("config.set", {"ok": True})

    result = await gw.config_set('{"logLevel": "DEBUG"}')

    _, params = gw.calls[-1]
    assert params["raw"] == '{"logLevel": "DEBUG"}'
    assert result["ok"] is True


async def test_config_patch_without_hash() -> None:
    gw = _make_gateway()
    gw.register("config.patch", {})

    await gw.config_patch('{"x": 1}')

    _, params = gw.calls[-1]
    assert params["raw"] == '{"x": 1}'
    assert "baseHash" not in params


async def test_config_patch_with_hash() -> None:
    gw = _make_gateway()
    gw.register("config.patch", {})

    await gw.config_patch('{"x": 1}', base_hash="h1")

    _, params = gw.calls[-1]
    assert params["raw"] == '{"x": 1}'
    assert params["baseHash"] == "h1"


async def test_config_apply_without_hash() -> None:
    gw = _make_gateway()
    gw.register("config.apply", {})

    await gw.config_apply('{"agents": {}}')

    _, params = gw.calls[-1]
    assert params["raw"] == '{"agents": {}}'
    assert "baseHash" not in params


async def test_config_apply_with_hash() -> None:
    gw = _make_gateway()
    gw.register("config.apply", {})

    await gw.config_apply('{"agents": {}}', base_hash="h2")

    _, params = gw.calls[-1]
    assert params["raw"] == '{"agents": {}}'
    assert params["baseHash"] == "h2"


# ------------------------------------------------------------------ #
# Approvals facade — exec.approval.resolve RPC
# ------------------------------------------------------------------ #


async def test_resolve_approval_approve() -> None:
    gw = _make_gateway()
    gw.register("exec.approval.resolve", {"ok": True})

    result = await gw.resolve_approval("r1", "approve")

    assert result == {"ok": True}
    gw.assert_called_with(
        "exec.approval.resolve",
        {"id": "r1", "decision": "approve"},
    )


async def test_resolve_approval_deny() -> None:
    gw = _make_gateway()
    gw.register("exec.approval.resolve", {"ok": True})

    result = await gw.resolve_approval("r1", "deny")

    assert result == {"ok": True}
    gw.assert_called_with(
        "exec.approval.resolve",
        {"id": "r1", "decision": "deny"},
    )


# ------------------------------------------------------------------ #
# Node / presence facade
# ------------------------------------------------------------------ #


async def test_system_presence() -> None:
    gw = _make_gateway()
    gw.register("system-presence", {"online": True})

    result = await gw.system_presence()

    assert result["online"] is True


async def test_node_list() -> None:
    gw = _make_gateway()
    gw.register("node.list", {"nodes": [{"id": "n1"}]})

    result = await gw.node_list()

    assert len(result) == 1


async def test_node_describe() -> None:
    gw = _make_gateway()
    gw.register("node.describe", {"id": "n1", "role": "worker"})

    result = await gw.node_describe("n1")

    assert result["role"] == "worker"


async def test_node_invoke_with_payload() -> None:
    gw = _make_gateway()
    gw.register("node.invoke", {"result": "done"})

    result = await gw.node_invoke("n1", "restart", payload={"force": True})

    _, params = gw.calls[-1]
    assert params["id"] == "n1"
    assert params["action"] == "restart"
    assert params["payload"] == {"force": True}
    assert result["result"] == "done"


async def test_node_invoke_without_payload() -> None:
    gw = _make_gateway()
    gw.register("node.invoke", {})

    await gw.node_invoke("n1", "ping")

    _, params = gw.calls[-1]
    assert "payload" not in params


# ------------------------------------------------------------------ #
# Ops facade
# ------------------------------------------------------------------ #


async def test_logs_tail_sends_empty_params() -> None:
    gw = _make_gateway()
    gw.register("logs.tail", {"file": "/log.txt", "lines": [{"msg": "hello"}]})

    result = await gw.logs_tail()

    _, params = gw.calls[-1]
    assert params == {}
    assert result["file"] == "/log.txt"


async def test_usage_summary_aggregates_from_sessions() -> None:
    gw = _make_gateway()
    gw.register(
        "sessions.list",
        {
            "sessions": [
                {"inputTokens": 100, "outputTokens": 50, "totalTokens": 150},
                {"inputTokens": 200, "outputTokens": 80, "totalTokens": 280},
            ]
        },
    )

    result = await gw.usage_summary()

    assert result["totalInputTokens"] == 300
    assert result["totalOutputTokens"] == 130
    assert result["totalTokens"] == 430
    assert result["sessionCount"] == 2
