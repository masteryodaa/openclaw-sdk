"""Phase 6F -- Models, Tools & System Discovery (4+ gateway methods).

Tests cover:
- All 4 gateway facade methods (models_list, tools_catalog, system_status,
  doctor_memory_status)
- ConfigManager discovery methods (discover_models, discover_tools)
- OpsManager status methods (system_status, memory_status)
- Response structure validation matching the spec
"""

from __future__ import annotations

from typing import Any

from openclaw_sdk.config.manager import ConfigManager
from openclaw_sdk.gateway.mock import MockGateway
from openclaw_sdk.ops.manager import OpsManager


# ------------------------------------------------------------------ #
# Realistic mock responses
# ------------------------------------------------------------------ #

_MODELS_LIST_RESPONSE: dict[str, Any] = {
    "models": [
        {
            "id": "claude-opus-4-6",
            "name": "Claude Opus 4.6",
            "provider": "anthropic",
            "contextWindow": 200000,
            "reasoning": True,
            "input": True,
        },
        {
            "id": "gpt-4o",
            "name": "GPT-4o",
            "provider": "openai",
            "contextWindow": 128000,
            "reasoning": False,
            "input": True,
        },
        {
            "id": "gemini-3-flash",
            "name": "Gemini 3 Flash",
            "provider": "google",
            "contextWindow": 1000000,
            "reasoning": False,
            "input": True,
        },
    ],
}

_TOOLS_CATALOG_RESPONSE: dict[str, Any] = {
    "agentId": "agent-001",
    "profiles": [
        {"id": "default", "label": "Default"},
        {"id": "coding", "label": "Coding"},
    ],
    "groups": [
        {
            "id": "web",
            "label": "Web Tools",
            "source": "builtin",
            "tools": [
                {
                    "id": "web-search",
                    "label": "Web Search",
                    "description": "Search the web for information",
                    "source": "builtin",
                    "defaultProfiles": ["default"],
                },
                {
                    "id": "web-fetch",
                    "label": "Web Fetch",
                    "description": "Fetch a web page",
                    "source": "builtin",
                    "defaultProfiles": ["default"],
                },
            ],
        },
        {
            "id": "fs",
            "label": "File System",
            "source": "builtin",
            "tools": [
                {
                    "id": "fs-read",
                    "label": "Read File",
                    "description": "Read a file from the filesystem",
                    "source": "builtin",
                    "defaultProfiles": ["default", "coding"],
                },
            ],
        },
    ],
}

_SYSTEM_STATUS_RESPONSE: dict[str, Any] = {
    "linkChannel": "ws://127.0.0.1:18789/gateway",
    "heartbeat": 1709142000000,
    "channelSummary": {"connected": 3, "total": 5},
    "queuedSystemEvents": 0,
    "sessions": {
        "paths": ["/sessions"],
        "count": 12,
        "defaults": {"model": "claude-opus-4-6"},
        "recent": ["agent:a1:main", "agent:a2:main"],
        "byAgent": {"a1": 5, "a2": 7},
    },
}

_DOCTOR_MEMORY_STATUS_RESPONSE: dict[str, Any] = {
    "agentId": "agent-001",
    "provider": "openai",
    "embedding": {
        "ok": True,
    },
}

_DOCTOR_MEMORY_STATUS_ERROR_RESPONSE: dict[str, Any] = {
    "agentId": "agent-002",
    "provider": "local",
    "embedding": {
        "ok": False,
        "error": "Embedding model not configured",
    },
}


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #


def _mock() -> MockGateway:
    mock = MockGateway()
    mock._connected = True
    return mock


def _make_config_manager() -> tuple[MockGateway, ConfigManager]:
    mock = _mock()
    return mock, ConfigManager(mock)


def _make_ops_manager() -> tuple[MockGateway, OpsManager]:
    mock = _mock()
    return mock, OpsManager(mock)


# ================================================================== #
# Gateway facade tests
# ================================================================== #


class TestGatewayModelsList:
    async def test_calls_correct_method(self) -> None:
        mock = _mock()
        mock.register("models.list", _MODELS_LIST_RESPONSE)

        result = await mock.models_list()

        mock.assert_called("models.list")
        assert "models" in result

    async def test_passes_empty_params(self) -> None:
        mock = _mock()
        mock.register("models.list", _MODELS_LIST_RESPONSE)

        await mock.models_list()

        _, params = mock.calls[-1]
        assert params == {}

    async def test_response_structure(self) -> None:
        mock = _mock()
        mock.register("models.list", _MODELS_LIST_RESPONSE)

        result = await mock.models_list()

        assert isinstance(result["models"], list)
        assert len(result["models"]) == 3
        model = result["models"][0]
        assert model["id"] == "claude-opus-4-6"
        assert model["provider"] == "anthropic"
        assert model["contextWindow"] == 200000
        assert model["reasoning"] is True
        assert model["input"] is True

    async def test_multiple_providers(self) -> None:
        mock = _mock()
        mock.register("models.list", _MODELS_LIST_RESPONSE)

        result = await mock.models_list()

        providers = {m["provider"] for m in result["models"]}
        assert providers == {"anthropic", "openai", "google"}


class TestGatewayToolsCatalog:
    async def test_calls_correct_method(self) -> None:
        mock = _mock()
        mock.register("tools.catalog", _TOOLS_CATALOG_RESPONSE)

        result = await mock.tools_catalog()

        mock.assert_called("tools.catalog")
        assert "groups" in result

    async def test_passes_empty_params(self) -> None:
        mock = _mock()
        mock.register("tools.catalog", _TOOLS_CATALOG_RESPONSE)

        await mock.tools_catalog()

        _, params = mock.calls[-1]
        assert params == {}

    async def test_response_structure(self) -> None:
        mock = _mock()
        mock.register("tools.catalog", _TOOLS_CATALOG_RESPONSE)

        result = await mock.tools_catalog()

        assert result["agentId"] == "agent-001"
        assert isinstance(result["profiles"], list)
        assert len(result["profiles"]) == 2
        assert result["profiles"][0]["id"] == "default"
        assert isinstance(result["groups"], list)
        assert len(result["groups"]) == 2

    async def test_tool_group_contents(self) -> None:
        mock = _mock()
        mock.register("tools.catalog", _TOOLS_CATALOG_RESPONSE)

        result = await mock.tools_catalog()

        web_group = result["groups"][0]
        assert web_group["id"] == "web"
        assert web_group["source"] == "builtin"
        assert len(web_group["tools"]) == 2
        tool = web_group["tools"][0]
        assert tool["id"] == "web-search"
        assert "description" in tool
        assert "defaultProfiles" in tool


class TestGatewaySystemStatus:
    async def test_calls_correct_method(self) -> None:
        mock = _mock()
        mock.register("status", _SYSTEM_STATUS_RESPONSE)

        result = await mock.system_status()

        mock.assert_called("status")
        assert "sessions" in result

    async def test_passes_empty_params(self) -> None:
        mock = _mock()
        mock.register("status", _SYSTEM_STATUS_RESPONSE)

        await mock.system_status()

        _, params = mock.calls[-1]
        assert params == {}

    async def test_response_structure(self) -> None:
        mock = _mock()
        mock.register("status", _SYSTEM_STATUS_RESPONSE)

        result = await mock.system_status()

        assert "linkChannel" in result
        assert "heartbeat" in result
        assert "channelSummary" in result
        assert "queuedSystemEvents" in result
        assert isinstance(result["sessions"], dict)
        assert result["sessions"]["count"] == 12

    async def test_sessions_detail(self) -> None:
        mock = _mock()
        mock.register("status", _SYSTEM_STATUS_RESPONSE)

        result = await mock.system_status()

        sessions = result["sessions"]
        assert "paths" in sessions
        assert "defaults" in sessions
        assert "recent" in sessions
        assert "byAgent" in sessions
        assert sessions["byAgent"]["a1"] == 5


class TestGatewayDoctorMemoryStatus:
    async def test_calls_correct_method(self) -> None:
        mock = _mock()
        mock.register("doctor.memory.status", _DOCTOR_MEMORY_STATUS_RESPONSE)

        result = await mock.doctor_memory_status()

        mock.assert_called("doctor.memory.status")
        assert "embedding" in result

    async def test_passes_empty_params(self) -> None:
        mock = _mock()
        mock.register("doctor.memory.status", _DOCTOR_MEMORY_STATUS_RESPONSE)

        await mock.doctor_memory_status()

        _, params = mock.calls[-1]
        assert params == {}

    async def test_response_structure_healthy(self) -> None:
        mock = _mock()
        mock.register("doctor.memory.status", _DOCTOR_MEMORY_STATUS_RESPONSE)

        result = await mock.doctor_memory_status()

        assert result["agentId"] == "agent-001"
        assert result["provider"] == "openai"
        assert result["embedding"]["ok"] is True
        assert "error" not in result["embedding"]

    async def test_response_structure_error(self) -> None:
        mock = _mock()
        mock.register("doctor.memory.status", _DOCTOR_MEMORY_STATUS_ERROR_RESPONSE)

        result = await mock.doctor_memory_status()

        assert result["agentId"] == "agent-002"
        assert result["embedding"]["ok"] is False
        assert result["embedding"]["error"] == "Embedding model not configured"


# ================================================================== #
# ConfigManager discovery method tests
# ================================================================== #


class TestConfigManagerDiscoverModels:
    async def test_calls_gateway(self) -> None:
        mock, mgr = _make_config_manager()
        mock.register("models.list", _MODELS_LIST_RESPONSE)

        result = await mgr.discover_models()

        mock.assert_called("models.list")
        assert "models" in result
        assert len(result["models"]) == 3

    async def test_passes_empty_params(self) -> None:
        mock, mgr = _make_config_manager()
        mock.register("models.list", _MODELS_LIST_RESPONSE)

        await mgr.discover_models()

        _, params = mock.calls[-1]
        assert params == {}

    async def test_returns_full_response(self) -> None:
        mock, mgr = _make_config_manager()
        mock.register("models.list", _MODELS_LIST_RESPONSE)

        result = await mgr.discover_models()

        model = result["models"][1]
        assert model["id"] == "gpt-4o"
        assert model["provider"] == "openai"


class TestConfigManagerDiscoverTools:
    async def test_calls_gateway(self) -> None:
        mock, mgr = _make_config_manager()
        mock.register("tools.catalog", _TOOLS_CATALOG_RESPONSE)

        result = await mgr.discover_tools()

        mock.assert_called("tools.catalog")
        assert "groups" in result
        assert "profiles" in result

    async def test_passes_empty_params(self) -> None:
        mock, mgr = _make_config_manager()
        mock.register("tools.catalog", _TOOLS_CATALOG_RESPONSE)

        await mgr.discover_tools()

        _, params = mock.calls[-1]
        assert params == {}

    async def test_returns_full_response(self) -> None:
        mock, mgr = _make_config_manager()
        mock.register("tools.catalog", _TOOLS_CATALOG_RESPONSE)

        result = await mgr.discover_tools()

        assert result["agentId"] == "agent-001"
        assert len(result["groups"]) == 2
        assert result["groups"][0]["tools"][0]["id"] == "web-search"


# ================================================================== #
# OpsManager status method tests
# ================================================================== #


class TestOpsManagerSystemStatus:
    async def test_calls_gateway(self) -> None:
        mock, mgr = _make_ops_manager()
        mock.register("status", _SYSTEM_STATUS_RESPONSE)

        result = await mgr.system_status()

        mock.assert_called("status")
        assert "sessions" in result

    async def test_passes_empty_params(self) -> None:
        mock, mgr = _make_ops_manager()
        mock.register("status", _SYSTEM_STATUS_RESPONSE)

        await mgr.system_status()

        _, params = mock.calls[-1]
        assert params == {}

    async def test_returns_full_response(self) -> None:
        mock, mgr = _make_ops_manager()
        mock.register("status", _SYSTEM_STATUS_RESPONSE)

        result = await mgr.system_status()

        assert result["linkChannel"] == "ws://127.0.0.1:18789/gateway"
        assert result["sessions"]["count"] == 12
        assert result["queuedSystemEvents"] == 0


class TestOpsManagerMemoryStatus:
    async def test_calls_gateway(self) -> None:
        mock, mgr = _make_ops_manager()
        mock.register("doctor.memory.status", _DOCTOR_MEMORY_STATUS_RESPONSE)

        result = await mgr.memory_status()

        mock.assert_called("doctor.memory.status")
        assert "embedding" in result

    async def test_passes_empty_params(self) -> None:
        mock, mgr = _make_ops_manager()
        mock.register("doctor.memory.status", _DOCTOR_MEMORY_STATUS_RESPONSE)

        await mgr.memory_status()

        _, params = mock.calls[-1]
        assert params == {}

    async def test_returns_healthy_response(self) -> None:
        mock, mgr = _make_ops_manager()
        mock.register("doctor.memory.status", _DOCTOR_MEMORY_STATUS_RESPONSE)

        result = await mgr.memory_status()

        assert result["agentId"] == "agent-001"
        assert result["provider"] == "openai"
        assert result["embedding"]["ok"] is True

    async def test_returns_error_response(self) -> None:
        mock, mgr = _make_ops_manager()
        mock.register("doctor.memory.status", _DOCTOR_MEMORY_STATUS_ERROR_RESPONSE)

        result = await mgr.memory_status()

        assert result["embedding"]["ok"] is False
        assert "error" in result["embedding"]


# ================================================================== #
# Existing methods still work (no regression)
# ================================================================== #


class TestOpsManagerExistingMethodsStillWork:
    """Ensure adding new methods doesn't break existing OpsManager methods."""

    async def test_logs_tail_still_works(self) -> None:
        mock, mgr = _make_ops_manager()
        mock.register("logs.tail", {"file": "app.log", "cursor": 0, "size": 100, "lines": []})

        result = await mgr.logs_tail()

        mock.assert_called("logs.tail")
        assert result["file"] == "app.log"

    async def test_usage_status_still_works(self) -> None:
        mock, mgr = _make_ops_manager()
        mock.register("usage.status", {"updatedAt": 1234, "providers": []})

        result = await mgr.usage_status()

        mock.assert_called("usage.status")
        assert "providers" in result

    async def test_usage_cost_still_works(self) -> None:
        mock, mgr = _make_ops_manager()
        mock.register("usage.cost", {"updatedAt": 1234, "days": 7, "daily": [], "totals": {}})

        result = await mgr.usage_cost()

        mock.assert_called("usage.cost")
        assert "totals" in result

    async def test_sessions_usage_still_works(self) -> None:
        mock, mgr = _make_ops_manager()
        mock.register(
            "sessions.usage",
            {"updatedAt": 1234, "startDate": "2026-01-01", "endDate": "2026-02-28", "sessions": []},
        )

        result = await mgr.sessions_usage()

        mock.assert_called("sessions.usage")
        assert "sessions" in result


class TestConfigManagerExistingMethodsStillWork:
    """Ensure adding new methods doesn't break existing ConfigManager methods."""

    async def test_get_still_works(self) -> None:
        mock, mgr = _make_config_manager()
        mock.register("config.get", {"path": "/config.json", "exists": True, "raw": "{}"})

        result = await mgr.get()

        mock.assert_called("config.get")
        assert result["exists"] is True

    async def test_schema_still_works(self) -> None:
        mock, mgr = _make_config_manager()
        mock.register("config.schema", {"schema": {"type": "object"}})

        result = await mgr.schema()

        mock.assert_called("config.schema")
        assert "schema" in result

    async def test_available_providers_still_works(self) -> None:
        providers = ConfigManager.available_providers()
        assert "anthropic" in providers
        assert "openai" in providers

    async def test_available_models_still_works(self) -> None:
        models = ConfigManager.available_models("anthropic")
        assert "anthropic" in models
        assert len(models["anthropic"]) > 0
