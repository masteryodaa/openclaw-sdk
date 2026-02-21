"""Tests for multitenancy module — Tenant, TenantConfig, TenantWorkspace."""
from __future__ import annotations

import pytest

from openclaw_sdk.core.client import OpenClawClient
from openclaw_sdk.core.config import AgentConfig, ClientConfig
from openclaw_sdk.core.constants import EventType
from openclaw_sdk.core.types import StreamEvent
from openclaw_sdk.gateway.mock import MockGateway
from openclaw_sdk.multitenancy.tenant import Tenant, TenantConfig
from openclaw_sdk.multitenancy.workspace import TenantWorkspace


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_workspace() -> tuple[TenantWorkspace, MockGateway]:
    """Create a TenantWorkspace backed by a connected MockGateway."""
    mock = MockGateway()
    await mock.connect()
    mock.register("config.get", {"raw": "{}", "exists": True, "path": "/mock"})
    mock.register("config.set", {"ok": True})
    client = OpenClawClient(config=ClientConfig(), gateway=mock)
    workspace = TenantWorkspace(client)
    return workspace, mock


def _tenant_config(
    tenant_id: str = "acme",
    name: str = "Acme Corp",
    **kwargs: object,
) -> TenantConfig:
    return TenantConfig(tenant_id=tenant_id, name=name, **kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Tenant model tests
# ---------------------------------------------------------------------------


class TestTenantConfig:
    def test_defaults(self) -> None:
        cfg = TenantConfig(tenant_id="t1", name="Test")
        assert cfg.max_agents == 10
        assert cfg.max_queries_per_hour == 1000
        assert cfg.max_cost_usd_per_day == 50.0
        assert "claude-sonnet-4-20250514" in cfg.allowed_models
        assert cfg.allowed_tools == []
        assert cfg.metadata == {}

    def test_custom_values(self) -> None:
        cfg = TenantConfig(
            tenant_id="t2",
            name="Custom",
            max_agents=3,
            max_queries_per_hour=100,
            max_cost_usd_per_day=5.0,
            allowed_models=["gpt-4o"],
            allowed_tools=["web-search"],
            metadata={"tier": "free"},
        )
        assert cfg.max_agents == 3
        assert cfg.allowed_models == ["gpt-4o"]
        assert cfg.metadata["tier"] == "free"


class TestTenant:
    def test_properties(self) -> None:
        tenant = Tenant(config=_tenant_config("acme", "Acme Corp"))
        assert tenant.tenant_id == "acme"
        assert tenant.name == "Acme Corp"
        assert tenant.is_active is True

    def test_can_create_agent_within_limit(self) -> None:
        tenant = Tenant(config=_tenant_config(max_agents=2))
        assert tenant.can_create_agent() is True
        tenant.agent_ids.append("a1")
        assert tenant.can_create_agent() is True
        tenant.agent_ids.append("a2")
        assert tenant.can_create_agent() is False

    def test_can_execute_active_within_budget(self) -> None:
        tenant = Tenant(config=_tenant_config(max_cost_usd_per_day=10.0))
        assert tenant.can_execute() is True

    def test_can_execute_inactive(self) -> None:
        tenant = Tenant(config=_tenant_config())
        tenant.is_active = False
        assert tenant.can_execute() is False

    def test_can_execute_over_budget(self) -> None:
        tenant = Tenant(config=_tenant_config(max_cost_usd_per_day=1.0))
        tenant.total_cost_usd = 1.5
        assert tenant.can_execute() is False

    def test_record_query(self) -> None:
        tenant = Tenant(config=_tenant_config())
        tenant.record_query(0.05)
        tenant.record_query(0.10)
        assert tenant.total_queries == 2
        assert abs(tenant.total_cost_usd - 0.15) < 1e-9

    def test_reset_daily_usage(self) -> None:
        tenant = Tenant(config=_tenant_config())
        tenant.total_cost_usd = 25.0
        tenant.total_queries = 100
        tenant.reset_daily_usage()
        assert tenant.total_cost_usd == 0.0
        # total_queries is NOT reset (lifetime counter)
        assert tenant.total_queries == 100


# ---------------------------------------------------------------------------
# TenantWorkspace — registration & lookup
# ---------------------------------------------------------------------------


class TestWorkspaceRegistration:
    @pytest.mark.asyncio
    async def test_register_tenant(self) -> None:
        workspace, _ = await _make_workspace()
        tenant = workspace.register_tenant(_tenant_config("acme", "Acme Corp"))
        assert tenant.tenant_id == "acme"
        assert tenant.name == "Acme Corp"

    @pytest.mark.asyncio
    async def test_register_duplicate_raises(self) -> None:
        workspace, _ = await _make_workspace()
        workspace.register_tenant(_tenant_config("acme", "Acme Corp"))
        with pytest.raises(ValueError, match="already registered"):
            workspace.register_tenant(_tenant_config("acme", "Acme Again"))

    @pytest.mark.asyncio
    async def test_get_tenant(self) -> None:
        workspace, _ = await _make_workspace()
        workspace.register_tenant(_tenant_config("acme", "Acme Corp"))
        tenant = workspace.get_tenant("acme")
        assert tenant.tenant_id == "acme"

    @pytest.mark.asyncio
    async def test_get_tenant_not_found_raises(self) -> None:
        workspace, _ = await _make_workspace()
        with pytest.raises(KeyError, match="not found"):
            workspace.get_tenant("nonexistent")

    @pytest.mark.asyncio
    async def test_list_tenants(self) -> None:
        workspace, _ = await _make_workspace()
        workspace.register_tenant(_tenant_config("acme", "Acme"))
        workspace.register_tenant(_tenant_config("beta", "Beta"))
        tenants = workspace.list_tenants()
        assert len(tenants) == 2
        ids = {t.tenant_id for t in tenants}
        assert ids == {"acme", "beta"}


# ---------------------------------------------------------------------------
# TenantWorkspace — agent creation
# ---------------------------------------------------------------------------


class TestWorkspaceAgentCreation:
    @pytest.mark.asyncio
    async def test_create_agent_namespaces_id(self) -> None:
        workspace, mock = await _make_workspace()
        workspace.register_tenant(_tenant_config("acme", "Acme Corp"))

        agent = await workspace.create_agent(
            "acme",
            AgentConfig(agent_id="support", system_prompt="Help users."),
        )
        assert agent.agent_id == "tenant-acme-support"
        tenant = workspace.get_tenant("acme")
        assert "tenant-acme-support" in tenant.agent_ids

    @pytest.mark.asyncio
    async def test_create_agent_exceeds_limit_raises(self) -> None:
        workspace, mock = await _make_workspace()
        workspace.register_tenant(_tenant_config("acme", "Acme", max_agents=1))

        # First agent succeeds
        await workspace.create_agent(
            "acme",
            AgentConfig(agent_id="bot1", system_prompt="first"),
        )

        # Second agent exceeds limit
        with pytest.raises(ValueError, match="agent limit"):
            await workspace.create_agent(
                "acme",
                AgentConfig(agent_id="bot2", system_prompt="second"),
            )

    @pytest.mark.asyncio
    async def test_create_agent_disallowed_model_raises(self) -> None:
        workspace, mock = await _make_workspace()
        workspace.register_tenant(
            _tenant_config("acme", "Acme", allowed_models=["gpt-4o-mini"])
        )

        # Default model is claude-sonnet-4-20250514, which is not in allowed list
        with pytest.raises(ValueError, match="not allowed"):
            await workspace.create_agent(
                "acme",
                AgentConfig(agent_id="bot", system_prompt="test"),
            )

    @pytest.mark.asyncio
    async def test_create_agent_allowed_model_succeeds(self) -> None:
        workspace, mock = await _make_workspace()
        workspace.register_tenant(
            _tenant_config("acme", "Acme", allowed_models=["claude-sonnet-4-20250514"])
        )

        agent = await workspace.create_agent(
            "acme",
            AgentConfig(
                agent_id="bot",
                system_prompt="test",
                llm_model="claude-sonnet-4-20250514",
            ),
        )
        assert agent.agent_id == "tenant-acme-bot"

    @pytest.mark.asyncio
    async def test_create_agent_empty_allowed_models_permits_all(self) -> None:
        workspace, mock = await _make_workspace()
        workspace.register_tenant(
            _tenant_config("acme", "Acme", allowed_models=[])
        )

        # Empty allowed_models means no restriction
        agent = await workspace.create_agent(
            "acme",
            AgentConfig(
                agent_id="bot",
                system_prompt="test",
                llm_model="some-exotic-model",
            ),
        )
        assert agent.agent_id == "tenant-acme-bot"


# ---------------------------------------------------------------------------
# TenantWorkspace — execution
# ---------------------------------------------------------------------------


class TestWorkspaceExecution:
    @pytest.mark.asyncio
    async def test_execute_tracks_usage(self) -> None:
        workspace, mock = await _make_workspace()
        workspace.register_tenant(_tenant_config("acme", "Acme"))

        # Create the agent first
        await workspace.create_agent(
            "acme",
            AgentConfig(agent_id="bot", system_prompt="test"),
        )

        # Set up mock for execute
        mock.register("chat.send", {"runId": "r1", "status": "started"})
        mock.emit_event(
            StreamEvent(
                event_type=EventType.DONE,
                data={
                    "payload": {
                        "runId": "r1",
                        "content": "response",
                        "usage": {
                            "input": 100,
                            "output": 50,
                            "totalTokens": 150,
                        },
                    }
                },
            )
        )

        result = await workspace.execute("acme", "bot", "hello")
        assert result.content == "response"

        tenant = workspace.get_tenant("acme")
        assert tenant.total_queries == 1
        # Cost = (100 * 3 + 50 * 15) / 1_000_000 = (300 + 750) / 1_000_000 = 0.00105
        assert tenant.total_cost_usd > 0

    @pytest.mark.asyncio
    async def test_execute_exceeds_cost_limit_raises(self) -> None:
        workspace, mock = await _make_workspace()
        workspace.register_tenant(
            _tenant_config("acme", "Acme", max_cost_usd_per_day=0.001)
        )

        # Create agent
        await workspace.create_agent(
            "acme",
            AgentConfig(agent_id="bot", system_prompt="test"),
        )

        # Manually set cost over the limit
        tenant = workspace.get_tenant("acme")
        tenant.total_cost_usd = 0.002  # Over 0.001 limit

        with pytest.raises(ValueError, match="exceeded usage limits"):
            await workspace.execute("acme", "bot", "hello")

    @pytest.mark.asyncio
    async def test_execute_zero_token_usage(self) -> None:
        workspace, mock = await _make_workspace()
        workspace.register_tenant(_tenant_config("acme", "Acme"))

        await workspace.create_agent(
            "acme",
            AgentConfig(agent_id="bot", system_prompt="test"),
        )

        # DONE event with no usage data
        mock.register("chat.send", {"runId": "r1", "status": "started"})
        mock.emit_event(
            StreamEvent(
                event_type=EventType.DONE,
                data={"payload": {"runId": "r1", "content": "response"}},
            )
        )

        result = await workspace.execute("acme", "bot", "hello")
        assert result.content == "response"

        tenant = workspace.get_tenant("acme")
        assert tenant.total_queries == 1
        # Zero usage => zero cost
        assert tenant.total_cost_usd == 0.0


# ---------------------------------------------------------------------------
# TenantWorkspace — activation / deactivation
# ---------------------------------------------------------------------------


class TestWorkspaceActivation:
    @pytest.mark.asyncio
    async def test_deactivate_blocks_execution(self) -> None:
        workspace, mock = await _make_workspace()
        workspace.register_tenant(_tenant_config("acme", "Acme"))
        await workspace.create_agent(
            "acme",
            AgentConfig(agent_id="bot", system_prompt="test"),
        )

        workspace.deactivate_tenant("acme")
        tenant = workspace.get_tenant("acme")
        assert tenant.is_active is False

        with pytest.raises(ValueError, match="exceeded usage limits"):
            await workspace.execute("acme", "bot", "hello")

    @pytest.mark.asyncio
    async def test_activate_re_enables(self) -> None:
        workspace, mock = await _make_workspace()
        workspace.register_tenant(_tenant_config("acme", "Acme"))
        await workspace.create_agent(
            "acme",
            AgentConfig(agent_id="bot", system_prompt="test"),
        )

        workspace.deactivate_tenant("acme")
        workspace.activate_tenant("acme")
        tenant = workspace.get_tenant("acme")
        assert tenant.is_active is True
        assert tenant.can_execute() is True


# ---------------------------------------------------------------------------
# TenantWorkspace — usage report
# ---------------------------------------------------------------------------


class TestUsageReport:
    @pytest.mark.asyncio
    async def test_usage_report(self) -> None:
        workspace, mock = await _make_workspace()
        workspace.register_tenant(
            _tenant_config("acme", "Acme Corp", max_cost_usd_per_day=100.0)
        )
        await workspace.create_agent(
            "acme",
            AgentConfig(agent_id="bot1", system_prompt="test"),
        )

        tenant = workspace.get_tenant("acme")
        tenant.record_query(5.0)
        tenant.record_query(10.0)

        report = workspace.get_usage_report("acme")
        assert report["tenant_id"] == "acme"
        assert report["name"] == "Acme Corp"
        assert report["is_active"] is True
        assert report["agents"] == 1
        assert report["max_agents"] == 10
        assert report["total_queries"] == 2
        assert abs(report["total_cost_usd"] - 15.0) < 1e-9
        assert report["max_cost_usd_per_day"] == 100.0
        assert abs(report["cost_utilization_pct"] - 15.0) < 1e-9

    @pytest.mark.asyncio
    async def test_usage_report_zero_max_cost(self) -> None:
        workspace, mock = await _make_workspace()
        workspace.register_tenant(
            _tenant_config("free", "Free Tier", max_cost_usd_per_day=0.0)
        )
        report = workspace.get_usage_report("free")
        assert report["cost_utilization_pct"] == 0.0

    @pytest.mark.asyncio
    async def test_usage_report_not_found_raises(self) -> None:
        workspace, _ = await _make_workspace()
        with pytest.raises(KeyError, match="not found"):
            workspace.get_usage_report("nonexistent")


# ---------------------------------------------------------------------------
# Integration: reset_daily_usage via workspace
# ---------------------------------------------------------------------------


class TestResetDailyUsage:
    @pytest.mark.asyncio
    async def test_reset_daily_usage(self) -> None:
        workspace, _ = await _make_workspace()
        workspace.register_tenant(_tenant_config("acme", "Acme"))
        tenant = workspace.get_tenant("acme")
        tenant.record_query(25.0)
        tenant.record_query(25.0)
        assert tenant.total_cost_usd == 50.0
        assert tenant.total_queries == 2

        tenant.reset_daily_usage()
        assert tenant.total_cost_usd == 0.0
        # total_queries is a lifetime counter, not reset
        assert tenant.total_queries == 2
        assert tenant.can_execute() is True


# ---------------------------------------------------------------------------
# Imports from top-level package
# ---------------------------------------------------------------------------


class TestTopLevelImports:
    def test_imports_from_package(self) -> None:
        from openclaw_sdk import Tenant, TenantConfig, TenantWorkspace

        assert Tenant is not None
        assert TenantConfig is not None
        assert TenantWorkspace is not None
