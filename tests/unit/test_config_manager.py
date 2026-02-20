"""Tests for ConfigManager (config.* gateway surface)."""

from __future__ import annotations

from openclaw_sdk.config.manager import ConfigManager
from openclaw_sdk.gateway.mock import MockGateway


def _make_manager() -> tuple[MockGateway, ConfigManager]:
    mock = MockGateway()
    mock._connected = True
    return mock, ConfigManager(mock)


async def test_get_calls_config_get() -> None:
    mock, mgr = _make_manager()
    mock.register("config.get", {"raw": '{"logLevel":"INFO"}', "parsed": {"logLevel": "INFO"}})

    result = await mgr.get()

    mock.assert_called("config.get")
    assert result["raw"] == '{"logLevel":"INFO"}'


async def test_schema_calls_config_schema() -> None:
    mock, mgr = _make_manager()
    mock.register("config.schema", {"schema": {"type": "object", "properties": {}}})

    result = await mgr.schema()

    mock.assert_called("config.schema")
    assert result["schema"]["type"] == "object"


async def test_set_sends_raw_string() -> None:
    mock, mgr = _make_manager()
    mock.register("config.set", {"ok": True})

    raw = '{"logLevel": "DEBUG"}'
    result = await mgr.set(raw)

    method, params = mock.calls[-1]
    assert method == "config.set"
    assert params["raw"] == raw
    assert result["ok"] is True


async def test_patch_sends_raw_without_hash() -> None:
    mock, mgr = _make_manager()
    mock.register("config.patch", {"hash": "abc123"})

    raw = '{"logLevel": "DEBUG"}'
    result = await mgr.patch(raw)

    method, params = mock.calls[-1]
    assert method == "config.patch"
    assert params["raw"] == raw
    assert "baseHash" not in params
    assert result["hash"] == "abc123"


async def test_patch_sends_base_hash_when_provided() -> None:
    mock, mgr = _make_manager()
    mock.register("config.patch", {})

    await mgr.patch('{"x": 1}', base_hash="hash-v2")

    _, params = mock.calls[-1]
    assert params["raw"] == '{"x": 1}'
    assert params["baseHash"] == "hash-v2"


async def test_apply_sends_raw_without_hash() -> None:
    mock, mgr = _make_manager()
    mock.register("config.apply", {"applied": True})

    raw = '{"agents": {"new-bot": {}}}'
    result = await mgr.apply(raw)

    method, params = mock.calls[-1]
    assert method == "config.apply"
    assert params["raw"] == raw
    assert "baseHash" not in params
    assert result["applied"] is True


async def test_apply_sends_base_hash_when_provided() -> None:
    mock, mgr = _make_manager()
    mock.register("config.apply", {})

    await mgr.apply('{"x": 1}', base_hash="etag-99")

    _, params = mock.calls[-1]
    assert params["baseHash"] == "etag-99"
