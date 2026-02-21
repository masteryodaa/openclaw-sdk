from __future__ import annotations

from typing import TYPE_CHECKING, Any

from openclaw_sdk.core.config import AgentConfig
from openclaw_sdk.multitenancy.tenant import Tenant, TenantConfig

if TYPE_CHECKING:
    from openclaw_sdk.core.agent import Agent
    from openclaw_sdk.core.client import OpenClawClient


class TenantWorkspace:
    """Manages isolated workspaces for multiple tenants.

    Each tenant gets their own set of agents with enforced quotas and
    model/tool restrictions.

    Example::

        workspace = TenantWorkspace(client)
        workspace.register_tenant(TenantConfig(
            tenant_id="acme",
            name="Acme Corp",
            max_agents=5,
            max_cost_usd_per_day=10.0,
        ))
        agent = await workspace.create_agent("acme", AgentConfig(
            agent_id="support",
            system_prompt="You are Acme support.",
        ))
        result = await workspace.execute("acme", "support", "Help me")
    """

    def __init__(self, client: OpenClawClient) -> None:
        self._client = client
        self._tenants: dict[str, Tenant] = {}

    def register_tenant(self, config: TenantConfig) -> Tenant:
        """Register a new tenant."""
        if config.tenant_id in self._tenants:
            raise ValueError(f"Tenant '{config.tenant_id}' already registered")
        tenant = Tenant(config=config)
        self._tenants[config.tenant_id] = tenant
        return tenant

    def get_tenant(self, tenant_id: str) -> Tenant:
        """Get a registered tenant."""
        if tenant_id not in self._tenants:
            raise KeyError(f"Tenant '{tenant_id}' not found")
        return self._tenants[tenant_id]

    def list_tenants(self) -> list[Tenant]:
        """List all registered tenants."""
        return list(self._tenants.values())

    def deactivate_tenant(self, tenant_id: str) -> None:
        """Deactivate a tenant (blocks new executions)."""
        self.get_tenant(tenant_id).is_active = False

    def activate_tenant(self, tenant_id: str) -> None:
        """Re-activate a tenant."""
        self.get_tenant(tenant_id).is_active = True

    async def create_agent(
        self,
        tenant_id: str,
        config: AgentConfig,
    ) -> Agent:
        """Create an agent for a tenant with quota enforcement."""
        tenant = self.get_tenant(tenant_id)

        if not tenant.can_create_agent():
            raise ValueError(
                f"Tenant '{tenant_id}' has reached the agent limit "
                f"({tenant.config.max_agents})"
            )

        # Namespace the agent ID to prevent collisions
        namespaced_id = f"tenant-{tenant_id}-{config.agent_id}"
        config.agent_id = namespaced_id

        # Enforce model restrictions
        if (
            tenant.config.allowed_models
            and config.llm_model not in tenant.config.allowed_models
        ):
            raise ValueError(
                f"Model '{config.llm_model}' not allowed for tenant '{tenant_id}'. "
                f"Allowed: {tenant.config.allowed_models}"
            )

        agent = await self._client.create_agent(config)
        tenant.agent_ids.append(namespaced_id)
        return agent

    async def execute(
        self,
        tenant_id: str,
        agent_id: str,
        query: str,
    ) -> Any:
        """Execute a query for a tenant with quota enforcement."""
        tenant = self.get_tenant(tenant_id)

        if not tenant.can_execute():
            raise ValueError(
                f"Tenant '{tenant_id}' has exceeded usage limits "
                f"(cost: ${tenant.total_cost_usd:.2f} / "
                f"${tenant.config.max_cost_usd_per_day:.2f})"
            )

        namespaced_id = f"tenant-{tenant_id}-{agent_id}"
        agent = self._client.get_agent(namespaced_id)
        result = await agent.execute(query)

        # Track usage
        cost = 0.0
        if result.token_usage:
            # Rough estimate: $3/M input + $15/M output (Sonnet pricing)
            cost = (result.token_usage.input * 3 + result.token_usage.output * 15) / 1_000_000
        tenant.record_query(cost)

        return result

    def get_usage_report(self, tenant_id: str) -> dict[str, Any]:
        """Get usage report for a tenant."""
        tenant = self.get_tenant(tenant_id)
        return {
            "tenant_id": tenant.tenant_id,
            "name": tenant.name,
            "is_active": tenant.is_active,
            "agents": len(tenant.agent_ids),
            "max_agents": tenant.config.max_agents,
            "total_queries": tenant.total_queries,
            "total_cost_usd": tenant.total_cost_usd,
            "max_cost_usd_per_day": tenant.config.max_cost_usd_per_day,
            "cost_utilization_pct": (
                (tenant.total_cost_usd / tenant.config.max_cost_usd_per_day * 100)
                if tenant.config.max_cost_usd_per_day > 0
                else 0.0
            ),
        }
