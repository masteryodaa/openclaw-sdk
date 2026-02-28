"""Tests for Phase 6C: Usage & Analytics (3 new gateway methods).

Covers:
- 3 new gateway facade methods on Gateway ABC (usage_status, usage_cost, sessions_usage)
- 3 new OpsManager methods (usage_status, usage_cost, sessions_usage)
- Backward compatibility of existing usage_summary() workaround
"""

from __future__ import annotations

from openclaw_sdk.gateway.mock import MockGateway
from openclaw_sdk.ops.manager import OpsManager

# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #


def _make_gateway() -> MockGateway:
    mock = MockGateway()
    mock._connected = True
    return mock


def _make_manager() -> tuple[MockGateway, OpsManager]:
    mock = _make_gateway()
    return mock, OpsManager(mock)


# ================================================================== #
# 1. Gateway facade: usage.status
# ================================================================== #


async def test_gateway_usage_status() -> None:
    gw = _make_gateway()
    gw.register(
        "usage.status",
        {
            "updatedAt": "2026-02-28T12:00:00Z",
            "providers": [
                {
                    "provider": "anthropic",
                    "displayName": "Anthropic",
                    "windows": [{"label": "daily", "usedPercent": 42.5}],
                    "plan": "pro",
                },
            ],
        },
    )

    result = await gw.usage_status()

    method, params = gw.calls[-1]
    assert method == "usage.status"
    assert params == {}
    assert result["updatedAt"] == "2026-02-28T12:00:00Z"
    assert len(result["providers"]) == 1
    assert result["providers"][0]["provider"] == "anthropic"
    assert result["providers"][0]["plan"] == "pro"


async def test_gateway_usage_status_empty_providers() -> None:
    gw = _make_gateway()
    gw.register("usage.status", {"updatedAt": "2026-02-28T12:00:00Z", "providers": []})

    result = await gw.usage_status()

    assert result["providers"] == []


# ================================================================== #
# 2. Gateway facade: usage.cost
# ================================================================== #


async def test_gateway_usage_cost() -> None:
    gw = _make_gateway()
    gw.register(
        "usage.cost",
        {
            "updatedAt": "2026-02-28T12:00:00Z",
            "days": 7,
            "daily": [
                {
                    "date": "2026-02-27",
                    "input": 1000,
                    "output": 500,
                    "cacheRead": 200,
                    "cacheWrite": 100,
                    "totalTokens": 1800,
                    "totalCost": 0.05,
                    "inputCost": 0.03,
                    "outputCost": 0.015,
                    "cacheReadCost": 0.003,
                    "cacheWriteCost": 0.002,
                    "missingCostEntries": 0,
                },
            ],
            "totals": {
                "input": 1000,
                "output": 500,
                "totalTokens": 1800,
                "totalCost": 0.05,
            },
        },
    )

    result = await gw.usage_cost()

    method, params = gw.calls[-1]
    assert method == "usage.cost"
    assert params == {}
    assert result["days"] == 7
    assert len(result["daily"]) == 1
    assert result["daily"][0]["date"] == "2026-02-27"
    assert result["daily"][0]["totalCost"] == 0.05
    assert result["totals"]["totalTokens"] == 1800


async def test_gateway_usage_cost_empty_daily() -> None:
    gw = _make_gateway()
    gw.register(
        "usage.cost",
        {"updatedAt": "2026-02-28T12:00:00Z", "days": 0, "daily": [], "totals": {}},
    )

    result = await gw.usage_cost()

    assert result["daily"] == []
    assert result["days"] == 0


# ================================================================== #
# 3. Gateway facade: sessions.usage
# ================================================================== #


async def test_gateway_sessions_usage() -> None:
    gw = _make_gateway()
    gw.register(
        "sessions.usage",
        {
            "updatedAt": "2026-02-28T12:00:00Z",
            "startDate": "2026-02-01",
            "endDate": "2026-02-28",
            "sessions": [
                {
                    "key": "agent:bot-a:main",
                    "sessionId": "sess-1",
                    "agentId": "bot-a",
                    "usage": {
                        "firstActivity": "2026-02-01T08:00:00Z",
                        "lastActivity": "2026-02-28T10:00:00Z",
                        "durationMs": 86400000,
                        "messageCounts": {"user": 10, "assistant": 10},
                        "toolUsage": {"bash": 5},
                        "modelUsage": {"claude-3-opus": 20},
                    },
                },
            ],
        },
    )

    result = await gw.sessions_usage()

    method, params = gw.calls[-1]
    assert method == "sessions.usage"
    assert params == {}
    assert result["startDate"] == "2026-02-01"
    assert result["endDate"] == "2026-02-28"
    assert len(result["sessions"]) == 1
    assert result["sessions"][0]["key"] == "agent:bot-a:main"
    assert result["sessions"][0]["usage"]["durationMs"] == 86400000


async def test_gateway_sessions_usage_empty_sessions() -> None:
    gw = _make_gateway()
    gw.register(
        "sessions.usage",
        {
            "updatedAt": "2026-02-28T12:00:00Z",
            "startDate": "2026-02-01",
            "endDate": "2026-02-28",
            "sessions": [],
        },
    )

    result = await gw.sessions_usage()

    assert result["sessions"] == []


async def test_gateway_sessions_usage_with_channel() -> None:
    """sessions.usage entries may include an optional channel field."""
    gw = _make_gateway()
    gw.register(
        "sessions.usage",
        {
            "updatedAt": "2026-02-28T12:00:00Z",
            "startDate": "2026-02-01",
            "endDate": "2026-02-28",
            "sessions": [
                {
                    "key": "agent:bot-a:main",
                    "sessionId": "sess-1",
                    "agentId": "bot-a",
                    "channel": "slack",
                    "usage": {"firstActivity": "2026-02-01T08:00:00Z"},
                },
            ],
        },
    )

    result = await gw.sessions_usage()

    assert result["sessions"][0]["channel"] == "slack"


# ================================================================== #
# 4. OpsManager.usage_status
# ================================================================== #


async def test_manager_usage_status() -> None:
    mock, mgr = _make_manager()
    mock.register(
        "usage.status",
        {
            "updatedAt": "2026-02-28T12:00:00Z",
            "providers": [
                {
                    "provider": "openai",
                    "displayName": "OpenAI",
                    "windows": [{"label": "monthly", "usedPercent": 80.0}],
                    "plan": "team",
                },
            ],
        },
    )

    result = await mgr.usage_status()

    mock.assert_called("usage.status")
    mock.assert_called_with("usage.status", {})
    assert result["providers"][0]["provider"] == "openai"
    assert result["providers"][0]["plan"] == "team"


# ================================================================== #
# 5. OpsManager.usage_cost
# ================================================================== #


async def test_manager_usage_cost() -> None:
    mock, mgr = _make_manager()
    mock.register(
        "usage.cost",
        {
            "updatedAt": "2026-02-28T12:00:00Z",
            "days": 30,
            "daily": [
                {
                    "date": "2026-02-01",
                    "input": 5000,
                    "output": 2500,
                    "totalTokens": 7500,
                    "totalCost": 0.25,
                },
            ],
            "totals": {"totalTokens": 7500, "totalCost": 0.25},
        },
    )

    result = await mgr.usage_cost()

    mock.assert_called("usage.cost")
    mock.assert_called_with("usage.cost", {})
    assert result["days"] == 30
    assert result["totals"]["totalCost"] == 0.25


# ================================================================== #
# 6. OpsManager.sessions_usage
# ================================================================== #


async def test_manager_sessions_usage() -> None:
    mock, mgr = _make_manager()
    mock.register(
        "sessions.usage",
        {
            "updatedAt": "2026-02-28T12:00:00Z",
            "startDate": "2026-02-01",
            "endDate": "2026-02-28",
            "sessions": [
                {
                    "key": "agent:bot-b:dev",
                    "sessionId": "sess-2",
                    "agentId": "bot-b",
                    "usage": {
                        "firstActivity": "2026-02-15T09:00:00Z",
                        "lastActivity": "2026-02-28T17:00:00Z",
                        "durationMs": 1209600000,
                        "messageCounts": {"user": 50, "assistant": 50},
                    },
                },
            ],
        },
    )

    result = await mgr.sessions_usage()

    mock.assert_called("sessions.usage")
    mock.assert_called_with("sessions.usage", {})
    assert len(result["sessions"]) == 1
    assert result["sessions"][0]["agentId"] == "bot-b"


# ================================================================== #
# 7. Backward compat: usage_summary() still works
# ================================================================== #


async def test_gateway_usage_summary_backward_compat() -> None:
    """The existing usage_summary() aggregation workaround still works."""
    gw = _make_gateway()
    gw.register(
        "sessions.list",
        {
            "sessions": [
                {"key": "agent:a:main", "inputTokens": 100, "outputTokens": 50, "totalTokens": 150},
                {"key": "agent:b:main", "inputTokens": 200, "outputTokens": 80, "totalTokens": 280},
            ],
        },
    )

    result = await gw.usage_summary()

    gw.assert_called("sessions.list")
    assert result["totalInputTokens"] == 300
    assert result["totalOutputTokens"] == 130
    assert result["totalTokens"] == 430
    assert result["sessionCount"] == 2


async def test_manager_usage_summary_backward_compat() -> None:
    """OpsManager.usage_summary() aggregation workaround still works."""
    mock, mgr = _make_manager()
    mock.register(
        "sessions.list",
        {
            "sessions": [
                {
                    "key": "agent:c:main",
                    "inputTokens": 500,
                    "outputTokens": 250,
                    "totalTokens": 750,
                },
            ],
        },
    )

    result = await mgr.usage_summary()

    mock.assert_called("sessions.list")
    assert result["totalInputTokens"] == 500
    assert result["totalOutputTokens"] == 250
    assert result["totalTokens"] == 750
    assert result["sessionCount"] == 1


# ================================================================== #
# 8. Gateway facade methods send empty params
# ================================================================== #


async def test_all_usage_methods_send_empty_params() -> None:
    """All three new methods send empty params dict."""
    gw = _make_gateway()
    gw.register("usage.status", {"providers": []})
    gw.register("usage.cost", {"daily": [], "totals": {}})
    gw.register("sessions.usage", {"sessions": []})

    await gw.usage_status()
    await gw.usage_cost()
    await gw.sessions_usage()

    assert len(gw.calls) == 3
    for method_name, params in gw.calls:
        assert params == {}, f"{method_name} should send empty params"
