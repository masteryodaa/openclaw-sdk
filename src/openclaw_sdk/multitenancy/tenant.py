from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TenantConfig(BaseModel):
    """Configuration for a tenant."""

    tenant_id: str
    name: str
    max_agents: int = 10
    max_queries_per_hour: int = 1000
    max_cost_usd_per_day: float = 50.0
    allowed_models: list[str] = Field(
        default_factory=lambda: ["claude-sonnet-4-20250514", "gpt-4o-mini"]
    )
    allowed_tools: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Tenant(BaseModel):
    """Represents a tenant with usage tracking."""

    config: TenantConfig
    agent_ids: list[str] = Field(default_factory=list)
    total_queries: int = 0
    total_cost_usd: float = 0.0
    is_active: bool = True

    @property
    def tenant_id(self) -> str:
        return self.config.tenant_id

    @property
    def name(self) -> str:
        return self.config.name

    def can_create_agent(self) -> bool:
        return len(self.agent_ids) < self.config.max_agents

    def can_execute(self) -> bool:
        return (
            self.is_active
            and self.total_cost_usd < self.config.max_cost_usd_per_day
        )

    def record_query(self, cost_usd: float = 0.0) -> None:
        self.total_queries += 1
        self.total_cost_usd += cost_usd

    def reset_daily_usage(self) -> None:
        self.total_cost_usd = 0.0
