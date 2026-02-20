"""Tests for OpsManager (logs.tail, usage aggregation)."""

from __future__ import annotations

from openclaw_sdk.ops.manager import OpsManager
from openclaw_sdk.gateway.mock import MockGateway


def _make_manager() -> tuple[MockGateway, OpsManager]:
    mock = MockGateway()
    mock._connected = True
    return mock, OpsManager(mock)


# ------------------------------------------------------------------ #
# logs_tail — no params, returns full dict
# ------------------------------------------------------------------ #


async def test_logs_tail_calls_gateway() -> None:
    mock, mgr = _make_manager()
    mock.register("logs.tail", {"file": "/var/log/oc.log", "lines": [{"msg": "hello"}]})

    result = await mgr.logs_tail()

    mock.assert_called("logs.tail")
    assert result["file"] == "/var/log/oc.log"
    assert len(result["lines"]) == 1


async def test_logs_tail_sends_empty_params() -> None:
    mock, mgr = _make_manager()
    mock.register("logs.tail", {"lines": []})

    await mgr.logs_tail()

    _, params = mock.calls[-1]
    assert params == {}


# ------------------------------------------------------------------ #
# usage_summary — aggregates from sessions.list
# ------------------------------------------------------------------ #


async def test_usage_summary_aggregates_from_sessions() -> None:
    mock, mgr = _make_manager()
    mock.register(
        "sessions.list",
        {
            "sessions": [
                {"key": "agent:a:main", "inputTokens": 100, "outputTokens": 50, "totalTokens": 150},
                {"key": "agent:b:main", "inputTokens": 200, "outputTokens": 80, "totalTokens": 280},
            ]
        },
    )

    result = await mgr.usage_summary()

    mock.assert_called("sessions.list")
    assert result["totalInputTokens"] == 300
    assert result["totalOutputTokens"] == 130
    assert result["totalTokens"] == 430
    assert result["sessionCount"] == 2


async def test_usage_summary_handles_empty_sessions() -> None:
    mock, mgr = _make_manager()
    mock.register("sessions.list", {"sessions": []})

    result = await mgr.usage_summary()

    assert result["totalInputTokens"] == 0
    assert result["totalOutputTokens"] == 0
    assert result["totalTokens"] == 0
    assert result["sessionCount"] == 0


async def test_usage_summary_handles_missing_token_fields() -> None:
    mock, mgr = _make_manager()
    mock.register(
        "sessions.list",
        {"sessions": [{"key": "agent:a:main"}]},
    )

    result = await mgr.usage_summary()

    assert result["totalInputTokens"] == 0
    assert result["totalTokens"] == 0
    assert result["sessionCount"] == 1
